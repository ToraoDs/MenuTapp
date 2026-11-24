import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Usuario
from ..schemas import EventoTokenOut, LoginIn, TokenOut, UsuarioOut
from ..security import (
    crear_token,
    crear_token_sse,
    usuario_actual,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == payload.usuario))
    if (
        usuario is None
        or not usuario.activo
        or not verify_password(payload.contrasena, usuario.contrasena_hash)
    ):
        logger.warning("Login fallido para usuario=%s", payload.usuario)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos"
        )
    logger.info("Login correcto usuario=%s rol=%s", usuario.usuario, usuario.rol.value)
    return TokenOut(
        access_token=crear_token(usuario), usuario=UsuarioOut.model_validate(usuario)
    )


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(usuario_actual)):
    return usuario


@router.post("/eventos-token", response_model=EventoTokenOut)
def eventos_token(usuario: Usuario = Depends(usuario_actual)):
    return EventoTokenOut(
        token=crear_token_sse(usuario),
        expira_en_segundos=settings.sse_token_ttl_seconds,
    )
