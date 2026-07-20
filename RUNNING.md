# Running the Afara Backend (for the frontend dev)

Hey 👋 — this is the API the app talks to. It handles translation, the Yorùbá
voice, and the tutor chat, and it stores recordings for our dataset. Speech-to-
text stays on the phone (on-device Whisper); the backend does everything else.

You can run the whole thing on your machine in about 3 minutes. No API keys
needed to start — it runs in a "demo" mode that returns placeholder AI responses
so you can wire up every screen before we plug in the real models.

---

## 1. What you need

- **Python 3.11+** installed. Check with `python --version`.
- That's it. No database, no Docker, no accounts.

---

## 2. Set it up (one time)

From a terminal, inside the `backend` folder:

```bash
python -m venv .venv
# activate it:
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1
#   Windows (Git Bash):    source .venv/Scripts/activate
#   Mac/Linux:             source .venv/bin/activate

pip install -r requirements.txt
```

---

## 3. Run it

```bash
uvicorn app.main:app --reload
```

You should see `Uvicorn running on http://127.0.0.1:8000`.

Open **http://localhost:8000/docs** in your browser. That's an interactive page
with every endpoint — click one, hit **"Try it out"**, **Execute**, and you see
the response. Great for poking at the API before writing any app code.

---

## 4. The base URL (important for real phones!)

- **iOS Simulator / web:** `http://localhost:8000`
- **Android emulator:** `http://10.0.2.2:8000` (localhost from inside the emulator)
- **A real phone on the same Wi-Fi:** use your computer's LAN IP, e.g.
  `http://192.168.1.42:8000`. Find it with `ipconfig` (Windows) / `ifconfig`
  (Mac). `localhost` on the phone means the *phone itself*, so it won't reach
  your server — this trips everyone up once.

Put the base URL in one config constant in the app so we can swap it for the
deployed URL later.

---

## 5. The endpoints (all under `/api/v1`)

| Method | Path              | Body            | What it does                          |
|--------|-------------------|-----------------|---------------------------------------|
| GET    | `/health`         | —               | Is it alive                           |
| GET    | `/languages`      | —               | The toggle options                    |
| POST   | `/translate`      | JSON            | Text → translated text (the hot path) |
| POST   | `/tts`            | JSON            | Text → spoken audio (WAV bytes)       |
| POST   | `/companion/chat` | JSON            | The tutor chat                        |
| POST   | `/utterances`     | form-data       | Upload a recording for the dataset    |

### Example calls from the app (fetch)

**Translate**
```js
const r = await fetch(`${BASE}/api/v1/translate`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "Báwo ni", source_lang: "yoruba", target_lang: "english" }),
});
const { translated_text } = await r.json();
```

**Companion chat**
```js
const r = await fetch(`${BASE}/api/v1/companion/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    messages: [{ role: "user", content: "Why is Báwo ni used here?" }],
  }),
});
const { reply } = await r.json();
```

**TTS (returns audio, not JSON)**
```js
// The response body IS the audio file. Save it, then play with expo-audio.
const r = await fetch(`${BASE}/api/v1/tts`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "Báwo ni", language: "yoruba" }),
});
const bytes = await r.arrayBuffer();       // raw WAV bytes
// write to a file with expo-file-system, then play the file URI with expo-audio
```

**Utterances (send the recording — multipart, not JSON)**
```js
const form = new FormData();
form.append("audio", { uri: recordingUri, name: "clip.m4a", type: "audio/m4a" });
form.append("transcript", transcriptText);
form.append("translation", translationText);
form.append("direction", "yoruba->english");
await fetch(`${BASE}/api/v1/utterances`, { method: "POST", body: form });
// Do this after each exchange — it's how we build the Ekiti dataset.
```

---

## 6. Demo mode vs real AI

Out of the box it's in **demo mode** (`MODEL_PROVIDER=stub`): `/translate` and
`/companion/chat` return obvious placeholder text, and `/tts` returns a tiny
silent clip. This is on purpose so you can build against real endpoints without
waiting on keys. The response *shapes* are identical to the real thing, so
nothing in the app changes when we switch.

To turn on the real stuff (optional, you usually don't need this to build the
UI): copy `.env.example` to `.env` and set `MODEL_PROVIDER=anthropic` (or
`openai`) with a key.

---

## 7. Optional: the real Yorùbá voice on your machine

`/tts` speaks real Yorùbá when you enable the local voice model. It's a heavier
install (downloads PyTorch + a ~150MB model the first time):

```bash
pip install -r requirements-tts.txt
# then set in .env:
TTS_PROVIDER=local
```

Restart the server. First boot takes ~15s to load the model (it warms up so the
first real request is fast), then each phrase is well under a second, and
repeated phrases are instant (cached). You don't need this to build screens —
demo mode is fine for that.

---

## 8. If something breaks

- **Port 8000 in use** → run `uvicorn app.main:app --reload --port 8001` and use
  that port.
- **Phone can't reach the server** → you're probably using `localhost`; use the
  computer's LAN IP (see section 4), and make sure both are on the same Wi-Fi.
- **CORS error in the browser build** → tell me and I'll add your origin; it's a
  one-line config (`CORS_ORIGINS`).
- **Local TTS crashes on import** → set `USE_TF=0` in your environment (there's a
  known TensorFlow/NumPy clash on some machines; the code already sets this, but
  the env var forces it).

Ping me on anything — happy to jump on it. The API contract (the request/response
shapes) is stable, so you can build confidently against it now.
