import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL(".", import.meta.url));
const PUBLIC_ROOT = resolve(ROOT, "public");
const MAX_AUDIO_BYTES = 10 * 1024 * 1024;
const MAX_REQUEST_BYTES = MAX_AUDIO_BYTES + 64 * 1024;
const DEFAULT_MODEL = "eleven_multilingual_sts_v2";
const UPSTREAM_TIMEOUT_MS = 90_000;
const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
};

export function loadEnvFile(contents, env = process.env) {
  for (const line of contents.split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!match || match[1] in env) continue;
    const value = match[2].replace(/^(['"])(.*)\1$/, "$2");
    env[match[1]] = value;
  }
  return env;
}

function jsonResponse(response, status, message, code) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  response.end(JSON.stringify({ error: message, code }));
}

function setSecurityHeaders(response) {
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("X-Frame-Options", "DENY");
  response.setHeader("Referrer-Policy", "no-referrer");
  response.setHeader("Permissions-Policy", "camera=(), geolocation=()");
  response.setHeader(
    "Content-Security-Policy",
    "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
  );
}

async function readBody(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_REQUEST_BYTES) {
      const error = new Error("The upload is too large.");
      error.status = 413;
      throw error;
    }
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

function userFacingUpstreamError(status) {
  if (status === 401 || status === 403) {
    return [502, "ElevenLabs rejected the server API key. Check ELEVENLABS_API_KEY and try again.", "INVALID_API_KEY"];
  }
  if (status === 402) {
    return [502, "Your ElevenLabs account needs available credits or a plan that supports speech-to-speech.", "CREDITS_REQUIRED"];
  }
  if (status === 422 || status === 400) {
    return [422, "ElevenLabs could not process this audio. Try a clear, short recording in a supported audio format.", "UNSUPPORTED_AUDIO"];
  }
  if (status === 429) {
    return [429, "ElevenLabs is receiving too many requests right now. Please wait a moment and try again.", "RATE_LIMITED"];
  }
  return [502, "ElevenLabs could not complete the transformation. Please try again shortly.", "PROVIDER_ERROR"];
}

async function handleTransform(request, response, { env, fetchImpl }) {
  const origin = request.headers.origin;
  if (origin) {
    try {
      const originUrl = new URL(origin);
      if (!["http:", "https:"].includes(originUrl.protocol) || originUrl.host !== request.headers.host) {
        jsonResponse(response, 403, "This request must come from the Voice Transformer page.", "INVALID_ORIGIN");
        request.resume();
        return;
      }
    } catch {
      jsonResponse(response, 403, "This request must come from the Voice Transformer page.", "INVALID_ORIGIN");
      request.resume();
      return;
    }
  }
  if (!env.ELEVENLABS_API_KEY?.trim()) {
    request.resume();
    jsonResponse(
      response,
      503,
      "Voice transformation is not configured yet. Add ELEVENLABS_API_KEY to voice-transformer/.env and restart the server.",
      "SETUP_REQUIRED",
    );
    return;
  }

  try {
    const contentType = request.headers["content-type"] || "";
    if (!contentType.toLowerCase().startsWith("multipart/form-data;")) {
      jsonResponse(response, 400, "Choose an audio file or record a clip before transforming.", "AUDIO_REQUIRED");
      return;
    }
    const contentLength = Number(request.headers["content-length"]);
    if (Number.isFinite(contentLength) && contentLength > MAX_REQUEST_BYTES) {
      jsonResponse(response, 413, "That audio file is too large. Choose a file smaller than 10 MB.", "FILE_TOO_LARGE");
      request.resume();
      return;
    }
    const body = await readBody(request);
    const form = await new Request("http://localhost/api/transform", {
      method: "POST",
      headers: { "content-type": contentType },
      body,
    }).formData();
    const audio = form.get("audio");
    const voiceId = String(form.get("voiceId") || "").trim();
    if (!(audio instanceof File) || audio.size === 0) {
      jsonResponse(response, 400, "Choose an audio file or record a clip before transforming.", "AUDIO_REQUIRED");
      return;
    }
    if (audio.size > MAX_AUDIO_BYTES) {
      jsonResponse(response, 413, "That audio file is too large. Choose a file smaller than 10 MB.", "FILE_TOO_LARGE");
      return;
    }
    const supportedExtension = /\.(mp3|wav|m4a|ogg|webm|aac|flac)$/i.test(audio.name);
    if (!(audio.type.startsWith("audio/") || audio.type === "application/octet-stream" || supportedExtension)) {
      jsonResponse(response, 415, "Please choose a supported audio file, such as MP3, WAV, M4A, OGG, or WebM.", "INVALID_AUDIO_TYPE");
      return;
    }
    if (!/^[A-Za-z0-9_-]{3,128}$/.test(voiceId)) {
      jsonResponse(response, 400, "Enter a valid ElevenLabs voice ID to use for the transformed speech.", "INVALID_VOICE_ID");
      return;
    }

    const upstreamForm = new FormData();
    upstreamForm.append("audio", new Blob([await audio.arrayBuffer()], { type: audio.type }), audio.name || "recording.webm");
    upstreamForm.append("model_id", DEFAULT_MODEL);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
    let upstream;
    try {
      upstream = await fetchImpl(
        `https://api.elevenlabs.io/v1/speech-to-speech/${encodeURIComponent(voiceId)}?output_format=mp3_44100_128`,
        {
          method: "POST",
          headers: { "xi-api-key": env.ELEVENLABS_API_KEY.trim() },
          body: upstreamForm,
          signal: controller.signal,
        },
      );
    } catch (error) {
      if (error.name === "AbortError") {
        jsonResponse(response, 504, "The transformation took too long. Try a shorter clip and try again.", "REQUEST_TIMEOUT");
      } else {
        jsonResponse(response, 502, "Could not reach ElevenLabs. Check your server connection and try again.", "PROVIDER_UNAVAILABLE");
      }
      return;
    } finally {
      clearTimeout(timeout);
    }

    if (!upstream.ok) {
      const [status, message, code] = userFacingUpstreamError(upstream.status);
      jsonResponse(response, status, message, code);
      return;
    }

    const transformedAudio = Buffer.from(await upstream.arrayBuffer());
    if (transformedAudio.length === 0) {
      jsonResponse(response, 502, "ElevenLabs returned an empty audio file. Please try again.", "EMPTY_AUDIO");
      return;
    }
    response.writeHead(200, {
      "Content-Type": "audio/mpeg",
      "Content-Length": transformedAudio.length,
      "Content-Disposition": 'inline; filename="transformed-voice.mp3"',
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });
    response.end(transformedAudio);
  } catch (error) {
    if (response.writableEnded) return;
    if (error.status === 413) {
      jsonResponse(response, 413, error.message, "FILE_TOO_LARGE");
      return;
    }
    jsonResponse(response, 400, "We could not read that upload. Please select a valid audio file and try again.", "INVALID_UPLOAD");
  }
}

async function serveStatic(pathname, response) {
  const fileName = pathname === "/" ? "index.html" : pathname.slice(1);
  const filePath = resolve(PUBLIC_ROOT, fileName);
  if (!filePath.startsWith(PUBLIC_ROOT + sep)) {
    response.writeHead(404).end("Not found");
    return;
  }
  try {
    const contents = await readFile(filePath);
    response.writeHead(200, {
      "Content-Type": MIME_TYPES[extname(filePath)] || "application/octet-stream",
      "Cache-Control": "no-cache",
    });
    response.end(contents);
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }).end("Not found");
  }
}

export function createAppServer({ env = process.env, fetchImpl = fetch } = {}) {
  return createServer(async (request, response) => {
    setSecurityHeaders(response);
    const pathname = new URL(request.url, "http://localhost").pathname;
    if (pathname === "/api/transform") {
      if (request.method !== "POST") {
        jsonResponse(response, 405, "Use POST to transform an audio clip.", "METHOD_NOT_ALLOWED");
        return;
      }
      await handleTransform(request, response, { env, fetchImpl });
      return;
    }
    if (request.method !== "GET") {
      response.writeHead(405, { Allow: "GET" }).end();
      return;
    }
    await serveStatic(pathname, response);
  });
}

async function start() {
  try {
    const envFile = await readFile(resolve(ROOT, ".env"), "utf8");
    loadEnvFile(envFile);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  const port = Number(process.env.PORT) || 3000;
  createAppServer().listen(port, "127.0.0.1", () => {
    console.log(`Voice Transformer is ready at http://localhost:${port}`);
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  start().catch((error) => {
    console.error("Could not start Voice Transformer:", error.message);
    process.exitCode = 1;
  });
}
