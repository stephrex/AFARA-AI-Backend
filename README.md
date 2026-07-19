# Afara Backend

Backend for Afara, a Yorùbá–English voice app for Ekiti State. You talk, it
transcribes, translates, and can read the translation back to the other person.
"Afara" is Yorùbá for "bridge".

This repo is just the API. The mobile app (Expo/React Native) lives in a
separate repo.

## How the pieces fit

We split the work between the phone and the server on purpose:

- The **phone** handles listening (speech-to-text runs on-device with Whisper).
  It's faster, works offline, and costs us nothing per request.
- The **server** handles the parts the phone can't do well:
  - translating the text
  - speaking Yorùbá out loud (phones don't ship a Yorùbá voice)
  - the AI tutor chat
  - storing the recordings so we can build our own Ekiti dataset over time

That last point matters. There is no good speech model for the Ekiti dialect
yet. Every time a user speaks and corrects the app, we keep that audio. Over
time that becomes a dataset nobody else has, and it's the whole reason Afara
can eventually beat the generic tools.

## Running it

You don't need Docker for local dev. Just Python and uvicorn.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

It starts on http://localhost:8000. Go to http://localhost:8000/docs for the
interactive API docs where you can click and test every endpoint.

It runs with no API keys out of the box. In this mode the AI responses are fake
placeholders so you can build and test the app end to end. When we're ready to
plug in real models, it's one setting (see below), no code changes.

## The endpoints

Everything is under `/api/v1`.

**GET /health** — is the server up, and which model mode is it in. Used by the
host (Render/Fly) to know the app is alive.

**GET /languages** — the two languages for the toggle. Returns Yorùbá and
English.

**POST /translate** — the main one. The phone sends the transcribed text, this
sends back the translation.
```json
{ "text": "Báwo ni", "source_lang": "yoruba", "target_lang": "english" }
```

**POST /tts** — turn text into spoken audio. Use this for the Yorùbá side (the
phone can already speak English for free). Returns audio bytes.
```json
{ "text": "Báwo ni", "language": "yoruba" }
```

**POST /companion/chat** — the tutor. The user asks things like "why is this
phrase used?" or "is this formal?" and gets an answer. Send the conversation so
far, get the next reply.
```json
{ "messages": [ { "role": "user", "content": "Why is Báwo ni used here?" } ] }
```

**POST /utterances** — the data collector. After a real exchange, the app
uploads the audio clip plus what was said and any correction the user made.
This is what quietly builds the Ekiti dataset. Sent as a file upload, not JSON.

```
audio (file), transcript, translation, direction, corrected_transcript,
user_id, session_id
```

## Turning on the real AI

All the model calls sit in one file: `app/services.py`. To go live, set these
in a `.env` file (copy `.env.example`):

```
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
```

`MODEL_PROVIDER` can be `stub` (default, fake responses), `anthropic`, or
`openai`. For Yorùbá speech (STT/TTS) we'll wire in Google Cloud or Spitch AI
in the same file. None of the endpoints change when we do this.

## Real Yorùbá voice (local TTS)

Phones can't speak Yorùbá, so we can run `facebook/mms-tts-yor` on the server
itself. To turn it on:

```
pip install -r requirements-tts.txt      # torch + transformers (heavy, one time)
# in .env:
TTS_PROVIDER=local
```

Now `POST /tts` returns real Yorùbá speech (a WAV file). It's built to be fast:

- the model loads **once** at startup and stays warm in memory — never per
  request, never re-downloaded per request (same idea as sentence-transformers)
- a warm-up pass runs at boot so the first real request is already quick
- `torch.inference_mode()` + CPU-thread tuning
- results are **cached by text** — a repeated phrase comes back instantly
- synthesis runs in a worker thread so it never blocks the server

The model is small (36M params); a CPU instance with ~1.5GB RAM runs it fine,
but it won't fit a 512MB free tier. Code is in `app/tts_local.py`.

Note: `mms-tts-yor` is non-commercial. Fine for demos; for a paid product point
`TTS_PROVIDER` at a commercially-cleared voice (Google `yo-NG` / Spitch AI) —
same endpoint, different branch in `app/services.py`.

## A note on Ekiti dialect

We checked the research. There is no speech model built for Ekiti. Every Yorùbá
model out there is trained on standard/Lagos Yorùbá, and even those get roughly
1 in 4 words wrong. So expect the Yorùbá side to be rough at first. That's
normal, and it's exactly why the `/utterances` collector exists.

## Deploying

- **Render:** connect this repo, set the root directory to `backend`. The
  `render.yaml` config is already here.
- **Fly.io:** `fly launch --no-deploy`, then `fly deploy`. Uses the `Dockerfile`
  and `fly.toml`.

Before going to production, set `CORS_ORIGINS` to the app's real origin instead
of `*`, and move the corpus storage from local disk to Postgres + S3/R2 (the
swap point is `app/storage.py`).

## Layout

```
app/
  main.py       app setup, CORS, routes mounted at /api/v1
  config.py     settings, read from environment / .env
  routes.py     the endpoints
  services.py   all AI calls (swap stub for real providers here)
  storage.py    saves recordings for the dataset
  schemas.py    request/response shapes
```
