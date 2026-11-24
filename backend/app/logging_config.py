import logging
from logging.config import dictConfig

from .config import settings


def configurar_logging() -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    handlers: dict[str, dict] = {
        "consola": {
            "class": "logging.StreamHandler",
            "formatter": "estandar",
            "level": settings.log_level,
        }
    }
    if settings.log_to_file:
        handlers["archivo"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detallado",
            "level": settings.log_level,
            "filename": str(settings.log_dir / "app.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        }

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "estandar": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s"
                },
                "detallado": {
                    "format": (
                        "%(asctime)s %(levelname)s %(name)s "
                        "%(filename)s:%(lineno)d %(message)s"
                    )
                },
            },
            "handlers": handlers,
            "root": {
                "handlers": list(handlers),
                "level": settings.log_level,
            },
            "loggers": {
                "uvicorn.access": {"handlers": [], "propagate": True},
                "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
            },
        }
    )


def obtener_logger(nombre: str) -> logging.Logger:
    return logging.getLogger(nombre)
