import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ..database import SessionLocal
from ..events import evento_bus
from ..models import AreaPreparacion, Rol
from ..security import usuario_desde_token

router = APIRouter(prefix="/api", tags=["eventos"])
logger = logging.getLogger(__name__)

TIEMPO_ESPERA = 15.0
TIPOS_MENU_MESA = frozenset({"menu_actualizado", "mesa_actualizada"})


def _visible(
    evento: dict,
    rol: Rol,
    area: AreaPreparacion | None,
    usuario_id: int,
) -> bool:
    tipo = evento.get("tipo")
    if tipo in TIPOS_MENU_MESA:
        return True
    if rol == Rol.ADMINISTRADOR:
        return True
    if rol == Rol.ENCARGADO_AREA:
        return (
            tipo in {"comanda_creada", "comanda_estado", "comanda_entregada", "comanda_impresa"}
            and evento.get("area") == (area.value if area else None)
        )
    if rol == Rol.PATINADOR:
        if tipo == "comanda_estado":
            return evento.get("estado") == "LISTO"
        return tipo == "comanda_entregada"
    if rol == Rol.MESERO:
        return (
            tipo in {"pedido_creado", "pedido_confirmado", "pedido_cancelado"}
            or tipo.startswith("comanda_")
        ) and evento.get("mesero_id") == usuario_id
    if rol == Rol.CAJERA:
        return tipo in {"cuenta_enviada_caja", "cuenta_pagada"}
    return False


async def _flujo(
    rol: Rol,
    area: AreaPreparacion | None,
    usuario_id: int,
) -> AsyncIterator[str]:
    cola = evento_bus.suscribir()
    try:
        yield "retry: 3000\n\n"
        while True:
            try:
                evento = await asyncio.wait_for(cola.get(), timeout=TIEMPO_ESPERA)
            except asyncio.TimeoutError:
                yield ": ping\n\n"
                continue
            if not _visible(evento, rol, area, usuario_id):
                continue
            datos = json.dumps(evento, ensure_ascii=False)
            yield (
                f"id: {evento['id']}\n"
                f"event: {evento['tipo']}\n"
                f"data: {datos}\n\n"
            )
    except asyncio.CancelledError:
        raise
    finally:
        evento_bus.desuscribir(cola)


@router.get("/eventos")
def eventos(token: str = Query(..., min_length=1)):
    with SessionLocal() as db:
        usuario = usuario_desde_token(token, db, tipos=("sse", "access"))
        rol = usuario.rol
        area = usuario.area
        usuario_id = usuario.id
        logger.info(
            "SSE autenticado usuario=%s rol=%s area=%s",
            usuario.username,
            rol.value,
            area.value if area else None,
        )

    return StreamingResponse(
        _flujo(rol, area, usuario_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
