from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../factory-regulation-monitoring
ENV_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8-sig",
        extra="ignore",
        case_sensitive=True,
    )

    smtp_host: str = Field(..., alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_user: str = Field(..., alias="SMTP_USER")
    smtp_password: str = Field(..., alias="SMTP_PASSWORD")

    mail_from: str = Field(..., alias="MAIL_FROM")
    isg_recipients: str = Field(..., alias="ISG_RECIPIENTS")


def get_settings() -> Settings:
    s = Settings()
    print(f"[DEBUG] ENV_PATH={ENV_PATH}")
    print(f"[DEBUG] smtp_host={s.smtp_host} smtp_port={s.smtp_port}")
    return s
