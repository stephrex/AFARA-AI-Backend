from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=()
    )

    app_name: str = "Afara API"
    environment: str = "development"

    # CORS — the Expo app / web build origin(s). "*" is fine for early demos.
    cors_origins: str = "*"

    # Which provider powers ASR + translation. "stub" returns canned data so
    # the API is fully runnable with no keys; swap to "openai" (or wire your
    # own) once the model-hosting decision is made.
    model_provider: str = "stub"

    # Only needed when model_provider="openai".
    openai_api_key: str | None = None
    translation_model: str = "gpt-4o-mini"

    # Companion tutor. Claude is a strong multilingual tutor; used only when
    # model_provider="anthropic". Swap for any model you prefer.
    anthropic_api_key: str | None = None
    chat_model: str = "claude-sonnet-5"

    # Text-to-speech provider, independent of the text model above.
    #   stub   — tiny placeholder bytes (default, no deps)
    #   local  — run facebook/mms-tts-yor inside this server (needs torch)
    #   openai — OpenAI TTS (English-only voices)
    tts_provider: str = "stub"
    local_tts_model: str = "facebook/mms-tts-yor"
    # CPU threads for local TTS; 0 = let torch decide.
    tts_num_threads: int = 0

    # Where the Ekiti corpus (audio + transcripts + corrections) is written.
    corpus_dir: str = "data/corpus"

    # Upload guardrails.
    max_audio_bytes: int = 25 * 1024 * 1024  # 25 MB

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
