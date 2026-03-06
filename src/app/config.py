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
        populate_by_name=True,
    )

    ollama_base_url: str = Field("http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    ollama_model: str = Field("qwen2.5:14b", validation_alias="OLLAMA_MODEL")

    smtp_host: str = Field(..., validation_alias="SMTP_HOST")
    smtp_port: int = Field(587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(..., validation_alias="SMTP_USER")
    smtp_password: str = Field(..., validation_alias="SMTP_PASSWORD")
    smtp_secure: bool = Field(True, validation_alias="SMTP_SECURE")
    smtp_auth: bool = Field(True, validation_alias="SMTP_AUTH")
    smtp_tls_reject_unauthorized: bool = Field(True, validation_alias="SMTP_TLS_REJECT_UNAUTHORIZED")
    smtp_enabled: bool = Field(True, validation_alias="SMTP_ENABLED")

    mail_from: str = Field(..., validation_alias="MAIL_FROM")
    admin_mail_enabled: bool = Field(True, validation_alias="ADMIN_MAIL_ENABLED")
    admin_recipients: str = Field("", validation_alias="ADMIN_RECIPIENTS")
    isg_recipients: str = Field(..., validation_alias="ISG_RECIPIENTS")
    ik_recipients: str = Field(..., validation_alias="IK_RECIPIENTS")
    muhasebe_recipients: str = Field(..., validation_alias="MUHASEBE_RECIPIENTS")
    lojistik_recipients: str = Field(..., validation_alias="LOJISTIK_RECIPIENTS")
    it_siber_recipients: str = Field("", validation_alias="IT_SIBER_RECIPIENTS")
    kvkk_recipients: str = Field("", validation_alias="KVKK_RECIPIENTS")


def get_settings() -> Settings:
    import os
    print(f"[DEBUG] ENV_PATH={ENV_PATH} exists={ENV_PATH.exists()}")
    print(f"[DEBUG] CWD={Path.cwd()}")
    print(f"[DEBUG] SMTP_HOST in env: {'SMTP_HOST' in os.environ}")
    try:
        s = Settings()
    except Exception:
        import traceback

        print("[ERROR] Failed to instantiate Settings():")
        print(traceback.format_exc())

        # Fallback: try to build settings from environment variables manually.
        # This helps when pydantic-settings failed to read the env file in container.
        env_map = {
            "ollama_base_url": "OLLAMA_BASE_URL",
            "ollama_model": "OLLAMA_MODEL",
            "smtp_host": "SMTP_HOST",
            "smtp_port": "SMTP_PORT",
            "smtp_user": "SMTP_USER",
            "smtp_password": "SMTP_PASSWORD",
            "smtp_secure": "SMTP_SECURE",
            "smtp_auth": "SMTP_AUTH",
            "smtp_tls_reject_unauthorized": "SMTP_TLS_REJECT_UNAUTHORIZED",
            "smtp_enabled": "SMTP_ENABLED",
            "mail_from": "MAIL_FROM",
            "admin_mail_enabled": "ADMIN_MAIL_ENABLED",
            "admin_recipients": "ADMIN_RECIPIENTS",
            "isg_recipients": "ISG_RECIPIENTS",
            "ik_recipients": "IK_RECIPIENTS",
            "muhasebe_recipients": "MUHASEBE_RECIPIENTS",
            "lojistik_recipients": "LOJISTIK_RECIPIENTS",
            "it_siber_recipients": "IT_SIBER_RECIPIENTS",
            "kvkk_recipients": "KVKK_RECIPIENTS",
        }

        def as_bool(v: str | None) -> bool | None:
            if v is None:
                return None
            return str(v).strip().lower() in ("1", "true", "yes", "y")

        fallback_kwargs: dict = {}
        for attr, env_key in env_map.items():
            val = os.getenv(env_key)
            if val is None:
                continue
            if attr == "smtp_port":
                try:
                    fallback_kwargs[attr] = int(val)
                except Exception:
                    fallback_kwargs[attr] = val
            elif attr in (
                "smtp_secure",
                "smtp_auth",
                "smtp_tls_reject_unauthorized",
                "smtp_enabled",
                "admin_mail_enabled",
            ):
                bool_val = as_bool(val)
                if bool_val is not None:
                    fallback_kwargs[attr] = bool_val
            else:
                fallback_kwargs[attr] = val

        # Provide sensible defaults for optional credentials
        fallback_kwargs.setdefault("smtp_user", "")
        fallback_kwargs.setdefault("smtp_password", "")

        try:
            s = Settings(**fallback_kwargs)
            print("[WARN] Settings() created from environment fallback.")
        except Exception:
            print("[ERROR] Fallback Settings() instantiation also failed:")
            print(traceback.format_exc())
            raise

    print(f"[DEBUG] smtp_host={s.smtp_host} smtp_port={s.smtp_port}")
    return s
