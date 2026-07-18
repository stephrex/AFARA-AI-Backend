from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from . import services, storage
from .config import Settings, get_settings
from .schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LanguageInfo,
    TranslateRequest,
    TranslateResponse,
    TTSRequest,
    UtteranceResponse,
)

router = APIRouter()

VALID_LANGS = {"yoruba", "english"}


def _check_lang(*langs: str) -> None:
    for lang in langs:
        if lang not in VALID_LANGS:
            raise HTTPException(422, f"Unsupported language: {lang}")


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #
@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health(settings: Settings = Depends(get_settings)):
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        model_provider=settings.model_provider,
    )


@router.get("/languages", response_model=list[LanguageInfo], tags=["meta"])
async def languages():
    return [
        LanguageInfo(code="yoruba", label="Yorùbá"),
        LanguageInfo(code="english", label="English"),
    ]


# --------------------------------------------------------------------------- #
# Core: translate (phone transcribes on-device, sends text here)
# --------------------------------------------------------------------------- #
@router.post("/translate", response_model=TranslateResponse, tags=["voice"])
async def translate(body: TranslateRequest, settings: Settings = Depends(get_settings)):
    """Text -> text between Yorùbá and English. This is the hot path: the
    device transcribes speech locally and posts the text here."""
    translated = await services.translate_text(
        body.text, body.source_lang, body.target_lang, settings
    )
    return TranslateResponse(
        translated_text=translated,
        source_lang=body.source_lang,
        target_lang=body.target_lang,
    )


# --------------------------------------------------------------------------- #
# TTS: speak the translation aloud (lazy — only when user taps play)
# --------------------------------------------------------------------------- #
@router.post("/tts", tags=["voice"])
async def tts(body: TTSRequest, settings: Settings = Depends(get_settings)):
    """Text -> spoken audio. Returns raw audio bytes."""
    _check_lang(body.language)
    audio = await services.synthesize_speech(body.text, body.language, settings)
    return Response(content=audio, media_type="audio/mpeg")


# --------------------------------------------------------------------------- #
# Companion tutor: the "chatting slide"
# --------------------------------------------------------------------------- #
@router.post("/companion/chat", response_model=ChatResponse, tags=["companion"])
async def companion_chat(body: ChatRequest, settings: Settings = Depends(get_settings)):
    """AI language companion. Send the running conversation, get a tutor reply."""
    reply = await services.companion_chat(body.messages, settings)
    return ChatResponse(reply=reply)


# --------------------------------------------------------------------------- #
# Corpus ingest: THE MOAT. Even with on-device transcription, upload the audio
# here so Afara accumulates the first annotated Ekiti-Yorùbá dataset.
# --------------------------------------------------------------------------- #
@router.post("/utterances", response_model=UtteranceResponse, tags=["corpus"])
async def log_utterance(
    audio: UploadFile | None = File(default=None, description="Raw recorded clip"),
    transcript: str | None = Form(default=None),
    translation: str | None = Form(default=None),
    direction: str = Form(default="yoruba->english"),
    corrected_transcript: str | None = Form(default=None),
    user_id: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
):
    """Persist one real exchange for the training corpus."""
    audio_bytes = None
    if audio is not None:
        audio_bytes = await audio.read()
        if len(audio_bytes) > settings.max_audio_bytes:
            raise HTTPException(413, "Audio file too large")

    uid, stored = storage.save_utterance(
        settings,
        audio_bytes=audio_bytes,
        filename=audio.filename if audio else None,
        meta={
            "transcript": transcript,
            "translation": translation,
            "direction": direction,
            "corrected_transcript": corrected_transcript,
            "user_id": user_id,
            "session_id": session_id,
        },
    )
    return UtteranceResponse(
        id=uid, audio_stored=stored, transcript=transcript, translation=translation
    )
