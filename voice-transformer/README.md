# Voice Transformer

A small, standalone browser app for recording or uploading a short speech clip and transforming its voice with ElevenLabs speech-to-speech. The server keeps your ElevenLabs API key private and returns the generated audio as an MP3 that you can preview or download.

## Requirements

- Node.js 20 or newer (no third-party packages required)
- An ElevenLabs account with an API key and access/credits for speech-to-speech
- A modern browser; microphone recording requires HTTPS or `localhost`

## Setup

1. Open a terminal in `voice-transformer/`.
2. Copy `.env.example` to `.env`.
   - PowerShell: `Copy-Item .env.example .env`
   - macOS/Linux: `cp .env.example .env`
3. Create an API key from [ElevenLabs API keys](https://elevenlabs.io/app/settings/api-keys). Add it to `.env`:

   ```dotenv
   ELEVENLABS_API_KEY=your_key_here
   PORT=3000
   ```

   The key is read only by the local server. Do not put it in browser code, commit it, or share it. `.env` is git-ignored.
4. Start the app:

   ```sh
   npm start
   ```

5. Open [http://127.0.0.1:3000](http://127.0.0.1:3000). If you chose a different `PORT`, use that port instead.

There are no npm dependencies to install. For automatic server restarts during development, run `npm run dev`.

## Use

1. Record a clip (up to 30 seconds) or upload an audio file (up to 10 MB).
2. Enter the ID of a voice available to your ElevenLabs account. You can find voices in the [Voice Library](https://elevenlabs.io/app/voice-library) or your account's Voices page.
3. Choose **Transform voice**. The app sends the clip to the server, which calls the ElevenLabs speech-to-speech API using `eleven_multilingual_sts_v2` and requests MP3 output.
4. Preview the result and use **Download MP3** if you want to keep it.

The input should contain clear speech. Supported uploads include common browser recordings (WebM/OGG/MP4) and MP3, WAV, and M4A files. The API key is never sent to the browser. Source and result audio are held in the browser for the current page session; source audio is sent to ElevenLabs only after you choose to transform it. Audio processing is subject to your ElevenLabs account settings and terms.

## Configuration and troubleshooting

- **“Voice transformation is not configured yet”** — create `voice-transformer/.env`, add `ELEVENLABS_API_KEY`, and restart the server.
- **“ElevenLabs rejected the server API key”** — check that the key is current and has the appropriate API permissions.
- **Credits or plan error** — verify your ElevenLabs account has available credits and supports voice conversion.
- **Unsupported audio** — try a clear, shorter recording in MP3, WAV, M4A, OGG, or WebM format.
- **Microphone access** — allow microphone permissions in your browser. Recording is available on `localhost` or an HTTPS deployment; uploading can be used instead.
- **Timeout or provider rate limit** — retry with a shorter clip after waiting briefly.

The server intentionally does not reveal raw provider responses or the API key to the page.

## Tests

Run the focused server/API tests without an API key:

```sh
npm test
```

Tests cover environment loading, missing-key handling, request validation, server-side API-key forwarding, MP3 response delivery, and friendly provider authentication errors. An actual voice transformation requires a valid user-provided ElevenLabs key, a usable voice ID, and account access/credits; it is not exercised by the automated tests.

## API behavior

`POST /api/transform` accepts multipart fields `audio` and `voiceId`. The server limits audio uploads to 10 MB, validates the voice ID, calls `POST /v1/speech-to-speech/{voice_id}` with the API key from the server environment, and returns MP3 audio. Configuration and provider errors return a JSON object with a readable `error` and stable `code`.
