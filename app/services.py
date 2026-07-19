"""Model-facing service layer.

Everything that touches an AI model lives behind these functions. The `stub`
provider makes the whole backend runnable with zero keys — perfect for wiring
up the frontend and deploying a live demo. Once keys land, flip MODEL_PROVIDER
and nothing else in the codebase changes.

Architecture note (post-meeting): speech-to-text now runs ON THE PHONE
(on-device Whisper), so there is no server transcription function here. The
server's job is translate, speak (TTS), and chat (the tutor).
"""

from __future__ import annotations

from .config import Settings
from .schemas import ChatMessage

LANGUAGE_LABELS = {"yoruba": "Yorùbá", "english": "English"}


# --------------------------------------------------------------------------- #
# Translation (text -> text) — the core hot path.
# --------------------------------------------------------------------------- #
async def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    settings: Settings,
) -> str:
    if source_lang == target_lang:
        return text
    if settings.model_provider == "openai":
        return await _openai_translate(text, source_lang, target_lang, settings)
    if settings.model_provider == "anthropic":
        return await _anthropic_translate(text, source_lang, target_lang, settings)
    # stub — echoes so the pipeline is observably wired end to end
    return f"[{LANGUAGE_LABELS[target_lang]} translation of] {text}"


def _translate_system(source_lang: str, target_lang: str) -> str:
    src, tgt = LANGUAGE_LABELS[source_lang], LANGUAGE_LABELS[target_lang]
    return (
        f"You are a translator for the Afara app. Translate the user's {src} "
        f"text into natural {tgt}. Reply with only the translation."
    )


async def _openai_translate(text, source_lang, target_lang, settings) -> str:
    from openai import AsyncOpenAI  # lazy import so stub mode needs no dep

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.translation_model,
        messages=[
            {"role": "system", "content": _translate_system(source_lang, target_lang)},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


async def _anthropic_translate(text, source_lang, target_lang, settings) -> str:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=settings.chat_model,
        max_tokens=1024,
        system=_translate_system(source_lang, target_lang),
        messages=[{"role": "user", "content": text}],
    )
    return resp.content[0].text.strip()


# --------------------------------------------------------------------------- #
# Companion tutor (chat) — the "chatting slide".
# --------------------------------------------------------------------------- #
COMPANION_SYSTEM = (
    "You are Afara's AI language companion — a warm, patient Yorùbá tutor. "
    "Help the user understand phrases, tone, formality, and usage. When they "
    "ask 'why', explain simply. Keep answers short and encouraging."
)


async def companion_chat(messages: list[ChatMessage], settings: Settings) -> str:
    if settings.model_provider == "anthropic":
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        resp = await client.messages.create(
            model=settings.chat_model,
            max_tokens=1024,
            system=COMPANION_SYSTEM,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return resp.content[0].text.strip()
    if settings.model_provider == "openai":
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=settings.translation_model,
            messages=[{"role": "system", "content": COMPANION_SYSTEM}]
            + [{"role": m.role, "content": m.content} for m in messages],
        )
        return resp.choices[0].message.content.strip()
    # stub
    last = messages[-1].content
    return (
        f"(demo tutor) Great question about “{last}”. Once an AI key is added, "
        "I'll explain the tone, formality, and give you another example."
    )


# --------------------------------------------------------------------------- #
# Text-to-speech (text -> audio) — lazy, only when the user taps play.
# Returns (audio_bytes, media_type).
# --------------------------------------------------------------------------- #
async def synthesize_speech(
    text: str, language: str, settings: Settings
) -> tuple[bytes, str]:
    if settings.tts_provider == "local":
        # Real Yorùbá voice via facebook/mms-tts-yor, running in this server.
        # The model is loaded once and kept warm; synthesis is CPU-bound so we
        # push it to a worker thread to keep the event loop free.
        from starlette.concurrency import run_in_threadpool

        from . import tts_local

        audio = await run_in_threadpool(
            tts_local.synthesize,
            text,
            settings.local_tts_model,
            settings.tts_num_threads,
        )
        return audio, "audio/wav"

    if settings.tts_provider == "openai":
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.audio.speech.create(
            model="tts-1", voice="alloy", input=text
        )
        return resp.read(), "audio/mpeg"

    # stub — tiny placeholder so clients get a 200 with audio bytes.
    return b"RIFF\x00\x00\x00\x00WAVEfmt ", "audio/wav"
