import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")


def _bool_env(nombre: str, defecto: bool) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _lista_env(nombre: str, defecto: list[str]) -> list[str]:
    valor = os.getenv(nombre)
    if not valor:
        return defecto
    return [elemento.strip() for elemento in valor.split(",") if elemento.strip()]


@dataclass(frozen=True)
class Settings:
    base_dir: Path = BASE_DIR
    project_dir: Path = PROJECT_DIR
    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'pdv.db'}"
    )
    secret_key: str = os.getenv(
        "SECRET_KEY", "dev-secret-cambiar-por-uno-largo-1234567890"
    )
    token_ttl_minutes: int = int(os.getenv("TOKEN_TTL_MINUTES", "480"))
    sse_token_ttl_seconds: int = int(os.getenv("SSE_TOKEN_TTL_SECONDS", "60"))
    frontend_dir: Path = Path(
        os.getenv("FRONTEND_DIR", str(PROJECT_DIR / "frontend"))
    )
    print_mode: str = os.getenv("PRINT_MODE", "file").strip().lower()
    print_dir: Path = Path(os.getenv("PRINT_DIR", str(BASE_DIR / "impresiones")))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    log_dir: Path = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))
    log_to_file: bool = _bool_env("LOG_TO_FILE", False)
    app_timezone: str = os.getenv("APP_TIMEZONE", "America/Bogota")
    mesas_total: int = int(os.getenv("MESAS_TOTAL", "46"))
    auto_create_db: bool = _bool_env("AUTO_CREATE_DB", True)
    sqlite_wal: bool = _bool_env("SQLITE_WAL", True)
    sqlite_busy_timeout_ms: int = int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "5000"))
    cors_origins: list[str] = field(
        default_factory=lambda: _lista_env("CORS_ORIGINS", ["*"])
    )


settings = Settings()
