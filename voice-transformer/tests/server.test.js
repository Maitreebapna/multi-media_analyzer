import assert from "node:assert/strict";
import { once } from "node:events";
import test from "node:test";
import { createAppServer, loadEnvFile } from "../server.js";

async function withServer(options, run) {
  const server = createAppServer(options);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  try {
    await run(`http://127.0.0.1:${server.address().port}`);
  } finally {
    server.close();
    await once(server, "close");
  }
}

test("loads environment values without replacing values already provided by the process", () => {
  const env = { EXISTING: "kept" };
  loadEnvFile("# comment\nEXISTING=overwritten\nELEVENLABS_API_KEY='example-key'\nPORT=4312\n", env);
  assert.deepEqual(env, { EXISTING: "kept", ELEVENLABS_API_KEY: "example-key", PORT: "4312" });
});

test("returns a friendly setup error when no server API key is configured", async () => {
  let upstreamCalled = false;
  await withServer({ env: {}, fetchImpl: async () => { upstreamCalled = true; } }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/transform`, { method: "POST" });
    const body = await response.json();
    assert.equal(response.status, 503);
    assert.equal(body.code, "SETUP_REQUIRED");
    assert.match(body.error, /ELEVENLABS_API_KEY/);
    assert.equal(upstreamCalled, false);
  });
});

test("serves the studio UI and blocks cross-origin transformation requests", async () => {
  let upstreamCalled = false;
  await withServer({
    env: { ELEVENLABS_API_KEY: "test-key" },
    fetchImpl: async () => { upstreamCalled = true; },
  }, async (baseUrl) => {
    const page = await fetch(baseUrl);
    assert.equal(page.status, 200);
    assert.match(page.headers.get("content-type"), /text\/html/);
    assert.match(await page.text(), /Bring in your voice/);

    const response = await fetch(`${baseUrl}/api/transform`, {
      method: "POST",
      headers: { origin: "https://untrusted.example" },
    });
    assert.equal(response.status, 403);
    assert.equal((await response.json()).code, "INVALID_ORIGIN");
    assert.equal(upstreamCalled, false);
  });
});

test("proxies audio to ElevenLabs without exposing the API key to the browser", async () => {
  let upstreamRequest;
  const audioBytes = new Uint8Array([1, 2, 3, 4]);
  const env = { ELEVENLABS_API_KEY: "server-only-test-key" };
  const fetchImpl = async (url, options) => {
    upstreamRequest = { url, options };
    return new Response(audioBytes, { status: 200, headers: { "content-type": "audio/mpeg" } });
  };
  await withServer({ env, fetchImpl }, async (baseUrl) => {
    const form = new FormData();
    form.append("audio", new Blob([new Uint8Array([9, 8, 7])], { type: "audio/wav" }), "sample.wav");
    form.append("voiceId", "voice_123");
    const response = await fetch(`${baseUrl}/api/transform`, { method: "POST", body: form });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("content-type"), "audio/mpeg");
    assert.deepEqual(new Uint8Array(await response.arrayBuffer()), audioBytes);
  });
  assert.match(upstreamRequest.url, /speech-to-speech\/voice_123\?output_format=mp3_44100_128$/);
  assert.equal(upstreamRequest.options.headers["xi-api-key"], "server-only-test-key");
  assert.equal(upstreamRequest.options.body.get("model_id"), "eleven_multilingual_sts_v2");
  assert.equal(upstreamRequest.options.body.get("audio").name, "sample.wav");
});

test("rejects malformed voice IDs without calling the provider", async () => {
  let upstreamCalled = false;
  await withServer({
    env: { ELEVENLABS_API_KEY: "test-key" },
    fetchImpl: async () => { upstreamCalled = true; },
  }, async (baseUrl) => {
    const form = new FormData();
    form.append("audio", new Blob([new Uint8Array([1])], { type: "audio/wav" }), "tiny.wav");
    form.append("voiceId", "../../secret");
    const response = await fetch(`${baseUrl}/api/transform`, { method: "POST", body: form });
    assert.equal(response.status, 400);
    assert.equal((await response.json()).code, "INVALID_VOICE_ID");
    assert.equal(upstreamCalled, false);
  });
});

test("maps provider authentication errors to an actionable message", async () => {
  await withServer({
    env: { ELEVENLABS_API_KEY: "bad-key" },
    fetchImpl: async () => new Response("details omitted", { status: 401 }),
  }, async (baseUrl) => {
    const form = new FormData();
    form.append("audio", new Blob([new Uint8Array([1])], { type: "audio/wav" }), "tiny.wav");
    form.append("voiceId", "voice_123");
    const response = await fetch(`${baseUrl}/api/transform`, { method: "POST", body: form });
    assert.equal(response.status, 502);
    const body = await response.json();
    assert.equal(body.code, "INVALID_API_KEY");
    assert.match(body.error, /Check ELEVENLABS_API_KEY/);
    assert.doesNotMatch(JSON.stringify(body), /bad-key/);
  });
});
