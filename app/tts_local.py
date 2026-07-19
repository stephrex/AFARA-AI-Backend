"""Local Yorùbá text-to-speech (facebook/mms-tts-yor, a VITS model).

Loaded ONCE and kept warm in memory — same idea as sentence-transformers. Every
call reuses the in-memory model; nothing is re-downloaded per request. Built for
speed:

  * model + tokenizer loaded a single time behind a lock (a warm singleton)
  * torch.inference_mode() — no autograd graph, faster and leaner than no_grad
  * CPU threads tuned to the machine
  * a warm-up pass at load time so the FIRST real request isn't the slow one
  * results cached by text hash — a repeated phrase returns instantly, no compute
  * synthesis is called from a worker thread (see services.py) so it never
    blocks the async server

Only imported when TTS_PROVIDER=local, so the default stub mode needs none of
these heavy dependencies.
"""

from __future__ import annotations

import os

# Force the PyTorch backend and never touch TensorFlow/Flax. transformers
# auto-detects any installed backend; if the box has a broken/mismatched TF
# (e.g. compiled against a different NumPy), importing a model would crash.
# These must be set before transformers is imported anywhere.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import hashlib
import io
import threading
import wave

_engine: "_VitsEngine | None" = None
_engine_lock = threading.Lock()

# Bounded most-recent cache of text -> WAV bytes. Common phrases (greetings,
# yes/no, numbers) repeat constantly in a translation app, so this pays off fast.
_cache: dict[str, bytes] = {}
_cache_order: list[str] = []
_CACHE_MAX = 512


class _VitsEngine:
    def __init__(self, model_name: str, num_threads: int):
        import torch
        from transformers import AutoTokenizer, VitsModel

        if num_threads and num_threads > 0:
            torch.set_num_threads(num_threads)

        self.torch = torch
        self.model = VitsModel.from_pretrained(model_name)
        self.model.eval()  # inference mode: disables dropout etc.
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.sampling_rate = int(self.model.config.sampling_rate)

        # Warm-up: run one tiny synthesis so lazy kernels/caches are primed and
        # the first real user gets the fast path.
        self.synth("báwo")

    def synth(self, text: str) -> bytes:
        torch = self.torch
        inputs = self.tokenizer(text, return_tensors="pt")
        with torch.inference_mode():
            waveform = self.model(**inputs).waveform  # (1, N) float32 in [-1, 1]
        audio = waveform.squeeze().detach().cpu().numpy()
        return _to_wav_bytes(audio, self.sampling_rate)


def _to_wav_bytes(audio, sampling_rate: int) -> bytes:
    """float32 [-1, 1] waveform -> 16-bit PCM WAV bytes (stdlib only)."""
    import numpy as np

    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sampling_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def preload(model_name: str, num_threads: int = 0) -> None:
    """Load + warm the engine now (call at server startup)."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = _VitsEngine(model_name, num_threads)


def synthesize(text: str, model_name: str, num_threads: int = 0) -> bytes:
    """Return WAV bytes for `text`. Cached by text; loads the model on first use."""
    key = hashlib.sha1(text.encode("utf-8")).hexdigest()
    hit = _cache.get(key)
    if hit is not None:
        return hit

    preload(model_name, num_threads)
    assert _engine is not None
    audio = _engine.synth(text)

    _cache[key] = audio
    _cache_order.append(key)
    if len(_cache_order) > _CACHE_MAX:
        _cache.pop(_cache_order.pop(0), None)
    return audio
