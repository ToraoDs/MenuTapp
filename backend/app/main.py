import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .config import settings
from .database import Base, SessionLocal, engine
from .events import evento_bus
from .logging_config import configurar_logging
from .routers import auth, cuentas, eventos, menu, pedidos, reportes, usuarios
from .seed import seed_if_empty
from .services import DomainError

configurar_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.print_dir.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_db:
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_if_empty(db)
    evento_bus.vincular_loop(asyncio.get_running_loop())
    logger.info(
        "PDV iniciado; db=%s print_dir=%s mesas=%s",
        settings.database_url,
        settings.print_dir,
        settings.mesas_total,
    )
    yield
    logger.info("PDV detenido")


app = FastAPI(title="PDV Restaurante", lifespan=lifespan)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, exc: IntegrityError):
    logger.warning("Conflicto de integridad: %s", exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "La operación entra en conflicto con datos existentes"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(menu.router)
app.include_router(pedidos.router)
app.include_router(cuentas.router)
app.include_router(reportes.router)
app.include_router(eventos.router)

if settings.frontend_dir.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=settings.frontend_dir, html=True),
        name="frontend",
    )
