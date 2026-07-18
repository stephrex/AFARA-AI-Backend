from typing import Literal

from pydantic import BaseModel, Field

# Afara currently bridges these two. Add to the Literal as you support more.
Language = Literal["yoruba", "english"]


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_lang: Language = "yoruba"
    target_lang: Language = "english"


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: Language
    target_lang: Language


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: Language = "yoruba"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """AI Language Companion (tutor) turn. Send the running conversation;
    optionally a user_id so the tutor can be personalized later."""

    messages: list[ChatMessage] = Field(..., min_length=1)
    user_id: str | None = None


class ChatResponse(BaseModel):
    reply: str


class UtteranceResponse(BaseModel):
    """Confirmation that a real exchange was captured for the corpus."""

    id: str
    audio_stored: bool
    transcript: str | None = None
    translation: str | None = None


class LanguageInfo(BaseModel):
    code: Language
    label: str


class HealthResponse(BaseModel):
    status: str
    environment: str
    model_provider: str
