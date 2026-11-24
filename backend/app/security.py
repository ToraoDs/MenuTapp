import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Rol, Usuario

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
TOKEN_TTL_MINUTES = settings.token_ttl_minutes
ITERACIONES = 210_000
bearer = HTTPBearer(auto_error=False)


def hash_password(contrasena: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", contrasena.encode(), salt, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${salt.hex()}${digest.hex()}"


def verify_password(contrasena: str, almacenado: str) -> bool:
    try:
        algoritmo, iteraciones, salt_hex, digest_hex = almacenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", contrasena.encode(), bytes.fromhex(salt_hex), int(iteraciones)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _codificar(usuario: Usuario, expira: timedelta, tipo: str) -> str:
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol.value,
        "tipo": tipo,
        "exp": datetime.now(timezone.utc) + expira,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def crear_token(usuario: Usuario) -> str:
    return _codificar(usuario, timedelta(minutes=TOKEN_TTL_MINUTES), "access")


def crear_token_sse(usuario: Usuario) -> str:
    return _codificar(
        usuario, timedelta(seconds=settings.sse_token_ttl_seconds), "sse"
    )


def decodificar_token(token: str, tipos: tuple[str, ...] = ("access",)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from exc

    if tipos and payload.get("tipo") not in tipos:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    if "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    return payload


def usuario_desde_token(
    token: str, db: Session, tipos: tuple[str, ...] = ("access",)
) -> Usuario:
    payload = decodificar_token(token, tipos)
    try:
        usuario_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from exc

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")
    return usuario


def usuario_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    return usuario_desde_token(credentials.credentials, db)


def requiere_roles(*roles: Rol):
    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso denegado")
        return usuario

    return dependencia
