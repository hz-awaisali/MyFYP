"""Application configuration loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Smart University Management System"
    APP_ENV: str = "development"  # development | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    # Example: postgresql+asyncpg://user:pass@host:5432/dbname
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sums"

    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Using pydantic's field_validator to automatically clean up the URL
    from pydantic import field_validator
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        return cls.assemble_db_connection(v)

    # --- Security / JWT ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_REFRESH_SECRET_KEY: str = "change-me-too-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- First super admin (seeded) ---
    SUPERADMIN_EMAIL: str = "admin@university.edu"
    SUPERADMIN_PASSWORD: str = "Admin@12345"
    SUPERADMIN_FULL_NAME: str = "Super Admin"

    # --- CORS ---
    CORS_ORIGINS: str = "*"  # comma-separated list, or "*"

    # --- File attachments ---
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_EXTENSIONS: str = "pdf,docx,png,jpg,jpeg"
    STORAGE_BACKEND: str = "b2"  # b2 | local
    PRESIGNED_URL_EXPIRE_SECONDS: int = 3600

    # --- Backblaze B2 (S3-compatible) ---
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_ENDPOINT_URL: str = ""  # e.g. https://s3.us-west-004.backblazeb2.com
    B2_REGION: str = "us-west-004"

    # --- Local storage fallback ---
    LOCAL_STORAGE_DIR: str = "uploads"

    # --- AI providers (later phase placeholders) ---
    AI_DEFAULT_PROVIDER: str = "openrouter"  # openrouter | groq | mock
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {e.strip().lower().lstrip(".") for e in self.ALLOWED_FILE_EXTENSIONS.split(",") if e.strip()}

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
