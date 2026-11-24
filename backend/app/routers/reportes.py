from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..database import get_db
from ..models import (
    AreaPreparacion,
    Cuenta,
    EstadoCuenta,
    LineaPedido,
    MetodoPago,
    Pago,
    Pedido,
    Rol,
)
from ..schemas import (
    ProductoVendidoOut,
    ReporteProductosOut,
    ReporteVentasOut,
    VentaAreaOut,
    VentaDiaOut,
    VentaMetodoOut,
)
from ..security import requiere_roles

router = APIRouter(prefix="/api/reportes", tags=["reportes"])
roles_reportes = requiere_roles(Rol.CAJERA, Rol.ADMINISTRADOR)
ZONA = ZoneInfo(settings.app_timezone)


def _rango(
    desde: date | None, hasta: date | None
) -> tuple[datetime, datetime, date, date]:
    if desde is None and hasta is None:
        hoy = datetime.now(ZONA).date()
        desde = hasta = hoy
    elif desde is None:
        desde = hasta
    elif hasta is None:
        hasta = desde

    assert desde is not None and hasta is not None
    if hasta < desde:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La fecha final no puede ser menor que la inicial",
        )
    if (hasta - desde).days > 366:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "El rango máximo es de 366 días",
        )

    inicio_local = datetime.combine(desde, time.min, tzinfo=ZONA)
    fin_local = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=ZONA)
    inicio = inicio_local.astimezone(timezone.utc).replace(tzinfo=None)
    fin = fin_local.astimezone(timezone.utc).replace(tzinfo=None)
    return inicio, fin, desde, hasta


def _cuentas_pagadas(
    db: Session, inicio: datetime, fin: datetime
) -> list[Cuenta]:
    query = (
        select(Cuenta)
        .where(
            Cuenta.estado == EstadoCuenta.PAGADA,
            Cuenta.cerrada_en >= inicio,
            Cuenta.cerrada_en < fin,
        )
        .options(
            selectinload(Cuenta.pago),
            selectinload(Cuenta.pedidos).selectinload(Pedido.lineas),
        )
    )
    return db.scalars(query).unique().all()


def _productos(
    db: Session, inicio: datetime, fin: datetime, limite: int
) -> list[ProductoVendidoOut]:
    cantidad = func.sum(LineaPedido.cantidad)
    total = func.sum(LineaPedido.precio_unitario * LineaPedido.cantidad)
    query = (
        select(
            LineaPedido.producto_id,
            LineaPedido.nombre,
            cantidad,
            total,
        )
        .join(Pedido, LineaPedido.pedido_id == Pedido.id)
        .join(Cuenta, Pedido.cuenta_id == Cuenta.id)
        .where(
            Cuenta.estado == EstadoCuenta.PAGADA,
            Cuenta.cerrada_en >= inicio,
            Cuenta.cerrada_en < fin,
            Pedido.cancelado_en.is_(None),
        )
        .group_by(LineaPedido.producto_id, LineaPedido.nombre)
        .order_by(total.desc())
        .limit(limite)
    )
    return [
        ProductoVendidoOut(
            producto_id=producto_id,
            producto=nombre,
            cantidad=int(cantidad_vendida or 0),
            total=int(total_vendido or 0),
        )
        for producto_id, nombre, cantidad_vendida, total_vendido in db.execute(query)
    ]


@router.get(
    "/ventas",
    response_model=ReporteVentasOut,
    dependencies=[Depends(roles_reportes)],
)
def ventas(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
):
    inicio, fin, desde_local, hasta_local = _rango(desde, hasta)
    cuentas = _cuentas_pagadas(db, inicio, fin)

    total_ventas = sum(
        cuenta.total_cobrado
        if cuenta.total_cobrado is not None
        else cuenta.total
        for cuenta in cuentas
    )
    cantidad_cuentas = len(cuentas)
    ticket_promedio = (
        round(total_ventas / cantidad_cuentas) if cantidad_cuentas else 0
    )

    por_metodo_datos: dict[MetodoPago, dict[str, int]] = {
        metodo: {"total": 0, "cuentas": 0} for metodo in MetodoPago
    }
    por_dia_datos: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "cuentas": 0}
    )
    for cuenta in cuentas:
        total = (
            cuenta.total_cobrado
            if cuenta.total_cobrado is not None
            else cuenta.total
        )
        if cuenta.pago is not None:
            datos = por_metodo_datos[cuenta.pago.metodo]
            datos["total"] += total
            datos["cuentas"] += 1
        if cuenta.cerrada_en is not None:
            fecha_local = (
                cuenta.cerrada_en.replace(tzinfo=timezone.utc)
                .astimezone(ZONA)
                .date()
                .isoformat()
            )
            por_dia_datos[fecha_local]["total"] += total
            por_dia_datos[fecha_local]["cuentas"] += 1

    area_query = (
        select(
            LineaPedido.area,
            func.sum(LineaPedido.precio_unitario * LineaPedido.cantidad),
            func.sum(LineaPedido.cantidad),
        )
        .join(Pedido, LineaPedido.pedido_id == Pedido.id)
        .join(Cuenta, Pedido.cuenta_id == Cuenta.id)
        .where(
            Cuenta.estado == EstadoCuenta.PAGADA,
            Cuenta.cerrada_en >= inicio,
            Cuenta.cerrada_en < fin,
            Pedido.cancelado_en.is_(None),
        )
        .group_by(LineaPedido.area)
    )
    por_area_datos = {
        area: {"total": 0, "cantidad": 0} for area in AreaPreparacion
    }
    for area, total, cantidad in db.execute(area_query):
        por_area_datos[area] = {
            "total": int(total or 0),
            "cantidad": int(cantidad or 0),
        }

    return ReporteVentasOut(
        desde=desde_local.isoformat(),
        hasta=hasta_local.isoformat(),
        zona_horaria=settings.app_timezone,
        total_ventas=total_ventas,
        cuentas_pagadas=cantidad_cuentas,
        ticket_promedio=ticket_promedio,
        por_metodo=[
            VentaMetodoOut(
                metodo=metodo,
                total=datos["total"],
                cuentas=datos["cuentas"],
            )
            for metodo, datos in por_metodo_datos.items()
        ],
        por_dia=[
            VentaDiaOut(fecha=fecha, total=datos["total"], cuentas=datos["cuentas"])
            for fecha, datos in sorted(por_dia_datos.items())
        ],
        por_area=[
            VentaAreaOut(
                area=area,
                total=datos["total"],
                cantidad=datos["cantidad"],
            )
            for area, datos in por_area_datos.items()
        ],
        top_productos=_productos(db, inicio, fin, 10),
    )


@router.get(
    "/productos",
    response_model=ReporteProductosOut,
    dependencies=[Depends(roles_reportes)],
)
def productos(
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    inicio, fin, desde_local, hasta_local = _rango(desde, hasta)
    return ReporteProductosOut(
        desde=desde_local.isoformat(),
        hasta=hasta_local.isoformat(),
        zona_horaria=settings.app_timezone,
        productos=_productos(db, inicio, fin, limite),
    )
