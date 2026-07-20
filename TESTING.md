# Testing the Afara Backend

Start the server (`uvicorn app.main:app --reload`), then test any endpoint.

**Easiest way:** open **http://localhost:8000/docs** — click an endpoint,
"Try it out", edit the payload, "Execute", see the response. No typing quotes.

Everything is under `/api/v1`.

---

## 1. Health
```
GET /api/v1/health
```
Expected: `{"status":"ok","environment":"development","model_provider":"stub"}`

## 2. Languages
```
GET /api/v1/languages
```
Expected: `[{"code":"yoruba","label":"Yorùbá"},{"code":"english","label":"English"}]`

## 3. Translate  (the core one)
```
POST /api/v1/translate
Content-Type: application/json

{ "text": "Báwo ni", "source_lang": "yoruba", "target_lang": "english" }
```
Expected: `{"translated_text":"...","source_lang":"yoruba","target_lang":"english"}`
(placeholder text in demo mode; real translation once an AI key is set)

## 4. Companion chat  (the tutor)
```
POST /api/v1/companion/chat
Content-Type: application/json

{ "messages": [ { "role": "user", "content": "Why is Báwo ni used here?" } ] }
```
Expected: `{"reply":"..."}`

## 5. TTS  (returns an audio file, not JSON)
```
POST /api/v1/tts
Content-Type: application/json

{ "text": "Báwo ni", "language": "yoruba" }
```
Expected: a WAV file. In demo mode it's a tiny placeholder; with
`TTS_PROVIDER=local` it's real Yorùbá speech (~1s). In /docs use the
"Download file" link to play it.

## 6. Utterances  (the dataset collector — form-data, not JSON)
```
POST /api/v1/utterances
Content-Type: multipart/form-data

transcript   = Báwo ni
translation  = How are you
direction    = yoruba->english
audio        = (optional file upload)
```
Expected: `{"id":"...","audio_stored":true,"transcript":"Báwo ni","translation":"How are you"}`

---

## curl versions (use Git Bash — cleaner quoting than PowerShell)

```bash
curl http://localhost:8000/api/v1/health

curl http://localhost:8000/api/v1/languages

curl -X POST http://localhost:8000/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"Báwo ni","source_lang":"yoruba","target_lang":"english"}'

curl -X POST http://localhost:8000/api/v1/companion/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Why is Báwo ni used?"}]}'

curl -X POST http://localhost:8000/api/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Báwo ni","language":"yoruba"}' --output test.wav

curl -X POST http://localhost:8000/api/v1/utterances \
  -F "transcript=Báwo ni" -F "translation=How are you" -F "direction=yoruba->english"
```

## What "passing" looks like
- 1, 2, 3, 4, 6 return real JSON responses in demo mode (no keys needed).
- 5 returns a valid WAV (placeholder audio in demo mode; real voice with
  `TTS_PROVIDER=local`).
- Every response is HTTP 200.
