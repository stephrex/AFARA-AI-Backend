# Afara API

FastAPI backend for **Afara** — a Yorùbá ↔ English voice bridge + language
tutor for Ekiti State. "Afara" means *bridge* in Yorùbá.

## Architecture (as of the frontend meeting)

Speech-to-text runs **on the phone** (on-device Whisper). So the backend does
**not** transcribe. Its job is:

1. **Translate** the text the phone sends (the hot path)
2. **Speak** the translation aloud in Yorùbá (TTS)
3. **Chat** — the AI language companion / tutor
4. **Collect the corpus** — every audio clip + transcript + correction, which
   becomes the first annotated Ekiti-Yorùbá dataset (the moat)

Runs out of the box in **stub mode** (no API keys, canned responses) so you can
wire up the frontend and deploy a live demo immediately, then flip
`MODEL_PROVIDER` to `anthropic` / `openai` when keys land.

## Run locally (no Docker needed)

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for interactive Swagger docs.

## Endpoints (prefix `/api/v1`)

| Method | Path               | Purpose                                                  |
|--------|--------------------|----------------------------------------------------------|
| GET    | `/health`          | Liveness + active model provider                         |
| GET    | `/languages`       | Supported languages for the toggle                       |
| POST   | `/translate`       | **Core.** Text → text (phone transcribes, posts text)    |
| POST   | `/tts`             | Text → spoken audio (Yorùbá voice; see note below)       |
| POST   | `/companion/chat`  | AI language tutor — the "chat" feature                   |
| POST   | `/utterances`      | Upload a real exchange (audio + transcript) → the corpus |

### `POST /translate`

```bash
curl -X POST http://localhost:8000/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"Báwo ni","source_lang":"yoruba","target_lang":"english"}'
```

### `POST /companion/chat`

```bash
curl -X POST http://localhost:8000/api/v1/companion/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Why is Báwo ni used here?"}]}'
```

### `POST /utterances` (the moat)

```bash
curl -X POST http://localhost:8000/api/v1/utterances \
  -F "audio=@clip.m4a" \
  -F "transcript=Báwo ni" \
  -F "translation=How are you" \
  -F "direction=yoruba->english"
```

## TTS: backend vs on-device

Phones can speak **English** with the built-in system voice (free, offline).
But **no phone ships a Yorùbá (yo-NG) system voice**, so the **Yorùbá** side
must come from the backend (Google Cloud TTS `yo-NG` or Spitch AI). Recommended
split: English TTS on-device, Yorùbá TTS via `/tts`.

## Wiring a real model

All model calls live in `app/services.py`. To go live:

```bash
# .env
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Uncomment the provider in `requirements.txt`. For Yorùbá STT/TTS wire Google
Cloud or Spitch AI in the same file — no route changes needed.

## Deploy

- **Render:** connect the repo, root dir `backend`; `render.yaml` included.
- **Fly.io:** `fly launch --no-deploy` then `fly deploy` (`Dockerfile` + `fly.toml`).

Set `CORS_ORIGINS` to your app's origin(s) before production. For a persistent
corpus in production, point storage at Postgres + object storage (S3/R2) —
see `app/storage.py`.
