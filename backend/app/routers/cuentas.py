from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..database import get_db
from ..models import (
    Comanda,
    Cuenta,
    EstadoCuenta,
    Mesa,
    Pedido,
    Rol,
    Usuario,
)
from ..schemas import CuentaOut, LineaOut, PagoIn, ReciboOut
from ..security import requiere_roles
from ..services import DomainError, enviar_cuenta_a_caja, registrar_pago

router = APIRouter(prefix="/api/cuentas", tags=["cuentas"])
roles_caja = requiere_roles(Rol.CAJERA, Rol.ADMINISTRADOR)
roles_envio = requiere_roles(Rol.MESERO, Rol.ADMINISTRADOR)
ZONA = ZoneInfo(settings.app_timezone)


def _opciones_cuenta():
    return (
        selectinload(Cuenta.mesa),
        selectinload(Cuenta.pago),
        selectinload(Cuenta.pedidos).selectinload(Pedido.lineas),
        selectinload(Cuenta.pedidos).selectinload(Pedido.comandas).selectinload(Comanda.lineas),
        selectinload(Cuenta.pedidos).selectinload(Pedido.mesero),
    )


def _cargar_cuenta(db: Session, cuenta_id: int) -> Cuenta:
    cuenta = db.scalar(
        select(Cuenta).where(Cuenta.id == cuenta_id).options(*_opciones_cuenta())
    )
    if cuenta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    return cuenta


def _recibo(cuenta: Cuenta) -> ReciboOut:
    pago = cuenta.pago
    if pago is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "La cuenta todavía no tiene pago registrado"
        )
    lineas = [
        linea
        for pedido in cuenta.pedidos
        if pedido.cancelado_en is None
        for linea in pedido.lineas
    ]
    total = cuenta.total_cobrado if cuenta.total_cobrado is not None else cuenta.total
    return ReciboOut(
        numero_recibo=pago.numero_recibo,
        cuenta_id=cuenta.id,
        mesa_numero=cuenta.mesa_numero,
        cerrada_en=cuenta.cerrada_en,
        lineas=[LineaOut.model_validate(linea) for linea in lineas],
        total=total,
        metodo=pago.metodo,
        valor=pago.valor,
        cambio=pago.cambio,
    )


@router.get("", response_model=list[CuentaOut], dependencies=[Depends(roles_caja)])
def listar_cuentas(
    estado: EstadoCuenta | None = None,
    mesa: int | None = None,
    enviada: bool | None = None,
    incluir_borradores: bool = False,
    desde: date | None = None,
    hasta: date | None = None,
    limite: int | None = Query(default=None, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(Cuenta).options(*_opciones_cuenta()).order_by(Cuenta.id.desc())

    if not incluir_borradores:
        confirmadas = (
            select(Pedido.cuenta_id)
            .join(Comanda, Comanda.pedido_id == Pedido.id)
            .where(Pedido.cancelado_en.is_(None))
            .distinct()
        )
        query = query.where(Cuenta.id.in_(confirmadas))
    if mesa is not None:
        query = query.join(Cuenta.mesa).where(Mesa.numero == mesa)
    if estado is not None:
        query = query.where(Cuenta.estado == estado)
    if enviada is not None:
        query = query.where(
            Cuenta.enviada_caja_en.is_not(None)
            if enviada
            else Cuenta.enviada_caja_en.is_(None)
        )
    if desde is not None:
        inicio = datetime.combine(desde, time.min, tzinfo=ZONA)
        query = query.where(
            Cuenta.abierta_en >= inicio.astimezone(timezone.utc).replace(tzinfo=None)
        )
    if hasta is not None:
        fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=ZONA)
        query = query.where(
            Cuenta.abierta_en < fin.astimezone(timezone.utc).replace(tzinfo=None)
        )
    if limite is not None:
        query = query.limit(limite)
    if offset:
        query = query.offset(offset)
    return db.scalars(query).unique().all()


@router.get("/mesa/{numero}", response_model=CuentaOut, dependencies=[Depends(roles_caja)])
def obtener_cuenta_por_mesa(numero: int, db: Session = Depends(get_db)):
    cuenta = db.scalar(
        select(Cuenta)
        .join(Cuenta.mesa)
        .where(Mesa.numero == numero, Cuenta.estado == EstadoCuenta.ABIERTA)
        .options(*_opciones_cuenta())
    )
    if cuenta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La mesa no tiene cuenta abierta")
    return cuenta


@router.get(
    "/{cuenta_id}", response_model=CuentaOut, dependencies=[Depends(roles_caja)]
)
def obtener_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    return _cargar_cuenta(db, cuenta_id)


@router.post("/{cuenta_id}/enviar-caja", response_model=CuentaOut)
def enviar_a_caja(
    cuenta_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_envio),
):
    cuenta = _cargar_cuenta(db, cuenta_id)
    if usuario.rol == Rol.MESERO and not any(
        pedido.mesero_id == usuario.id and pedido.cancelado_en is None
        for pedido in cuenta.pedidos
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La cuenta no tiene pedidos de este mesero"
        )
    try:
        enviar_cuenta_a_caja(db, cuenta)
    except DomainError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    return _cargar_cuenta(db, cuenta_id)


@router.post(
    "/{cuenta_id}/pagar",
    response_model=ReciboOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(roles_caja)],
)
def pagar(cuenta_id: int, payload: PagoIn, db: Session = Depends(get_db)):
    cuenta = _cargar_cuenta(db, cuenta_id)
    try:
        registrar_pago(db, cuenta, payload.metodo, payload.valor)
    except DomainError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    return _recibo(_cargar_cuenta(db, cuenta_id))


@router.get(
    "/{cuenta_id}/recibo",
    response_model=ReciboOut,
    dependencies=[Depends(roles_caja)],
)
def recibo(cuenta_id: int, db: Session = Depends(get_db)):
    return _recibo(_cargar_cuenta(db, cuenta_id))
