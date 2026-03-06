from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../factory-regulation-monitoring
ENV_PATH = PROJECT_ROOT / ".env"

# Fallback: if .env not found at project root, try working directory
if not ENV_PATH.exists():
    ENV_PATH = Path.cwd() / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8-sig",
        extra="ignore",
        case_sensitive=True,
    )

    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field("qwen2.5:14b", alias="OLLAMA_MODEL")

    smtp_host: str = Field(..., alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_user: str = Field(..., alias="SMTP_USER")
    smtp_password: str = Field(..., alias="SMTP_PASSWORD")
    smtp_secure: bool = Field(True, alias="SMTP_SECURE")
    smtp_auth: bool = Field(True, alias="SMTP_AUTH")
    smtp_tls_reject_unauthorized: bool = Field(True, alias="SMTP_TLS_REJECT_UNAUTHORIZED")
    smtp_enabled: bool = Field(True, alias="SMTP_ENABLED")

    mail_from: str = Field(..., alias="MAIL_FROM")
    admin_mail_enabled: bool = Field(True, alias="ADMIN_MAIL_ENABLED")
    admin_recipients: str = Field("", alias="ADMIN_RECIPIENTS")
    isg_recipients: str = Field(..., alias="ISG_RECIPIENTS")
    ik_recipients: str = Field(..., alias="IK_RECIPIENTS")
    muhasebe_recipients: str = Field(..., alias="MUHASEBE_RECIPIENTS")
    lojistik_recipients: str = Field(..., alias="LOJISTIK_RECIPIENTS")


def get_settings() -> Settings:
    s = Settings()
    print(f"[DEBUG] ENV_PATH={ENV_PATH}")
    print(f"[DEBUG] smtp_host={s.smtp_host} smtp_port={s.smtp_port}")
    return s
