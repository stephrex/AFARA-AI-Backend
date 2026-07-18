"""Corpus storage — the moat.

Every real exchange (audio + transcript + translation + any user correction)
is persisted here so Afara accumulates the first annotated Ekiti-Yoruba
dataset. Today this writes to local disk (audio files + a JSONL index) so it
runs with zero external services. Swap the two functions below for
Postgres + object storage (S3/R2) when you deploy for real — nothing else
changes.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from .config import Settings


def _paths(settings: Settings) -> tuple[str, str]:
    audio_dir = os.path.join(settings.corpus_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    index = os.path.join(settings.corpus_dir, "utterances.jsonl")
    return audio_dir, index


def save_utterance(
    settings: Settings,
    *,
    audio_bytes: bytes | None,
    filename: str | None,
    meta: dict,
) -> tuple[str, bool]:
    """Persist one exchange. Returns (id, audio_stored)."""
    audio_dir, index = _paths(settings)
    uid = uuid.uuid4().hex
    audio_stored = False

    if audio_bytes:
        ext = os.path.splitext(filename or "")[1] or ".m4a"
        with open(os.path.join(audio_dir, f"{uid}{ext}"), "wb") as f:
            f.write(audio_bytes)
        audio_stored = True

    record = {
        "id": uid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audio_file": f"{uid}{ext}" if audio_stored else None,
        **meta,
    }
    with open(index, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return uid, audio_stored
