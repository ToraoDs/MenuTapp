import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..events import evento_bus
from ..impresion import imprimir_comanda, ruta_archivo
from ..models import (
    AreaPreparacion,
    Comanda,
    Cuenta,
    EstadoComanda,
    Mesa,
    Pedido,
    Rol,
    Usuario,
)
from ..schemas import (
    ComandaOut,
    EstadoComandaIn,
    PedidoIn,
    PedidoOut,
)
from ..security import requiere_roles
from ..services import (
    DomainError,
    cambiar_estado_comanda,
    cancelar_pedido,
    confirmar_pedido,
    crear_pedido,
    puede_modificarse,
    reemplazar_lineas,
)

router = APIRouter(prefix="/api", tags=["pedidos"])
logger = logging.getLogger(__name__)

roles_pedido = requiere_roles(Rol.MESERO, Rol.ADMINISTRADOR)
roles_comanda = requiere_roles(Rol.ENCARGADO_AREA, Rol.PATINADOR, Rol.ADMINISTRADOR)
roles_estado = requiere_roles(Rol.ENCARGADO_AREA, Rol.ADMINISTRADOR)
roles_entrega = requiere_roles(Rol.PATINADOR, Rol.MESERO, Rol.ADMINISTRADOR)
roles_impresion = requiere_roles(Rol.ENCARGADO_AREA, Rol.ADMINISTRADOR)


def _opciones_pedido():
    return (
        selectinload(Pedido.lineas),
        selectinload(Pedido.comandas).selectinload(Comanda.lineas),
        selectinload(Pedido.mesero),
        selectinload(Pedido.cuenta).selectinload(Cuenta.mesa),
    )


def _cargar_pedido(db: Session, pedido_id: int) -> Pedido:
    pedido = db.scalar(
        select(Pedido).where(Pedido.id == pedido_id).options(*_opciones_pedido())
    )
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return pedido


def _opciones_comanda():
    return (
        selectinload(Comanda.lineas),
        selectinload(Comanda.pedido).selectinload(Pedido.mesero),
        selectinload(Comanda.pedido)
        .selectinload(Pedido.cuenta)
        .selectinload(Cuenta.mesa),
    )


def _cargar_comanda(db: Session, comanda_id: int) -> Comanda:
    comanda = db.scalar(
        select(Comanda).where(Comanda.id == comanda_id).options(*_opciones_comanda())
    )
    if comanda is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comanda no encontrada")
    return comanda


def _validar_propietario(pedido: Pedido, usuario: Usuario) -> None:
    if usuario.rol == Rol.MESERO and pedido.mesero_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este pedido no es tuyo")


@router.post(
    "/pedidos", response_model=PedidoOut, status_code=status.HTTP_201_CREATED
)
def nuevo_pedido(
    payload: PedidoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_pedido),
):
    pedido = crear_pedido(db, payload, usuario)
    return _cargar_pedido(db, pedido.id)


@router.get("/pedidos", response_model=list[PedidoOut])
def listar_pedidos(
    mesa: int | None = None,
    solo_mios: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_pedido),
):
    query = select(Pedido).options(*_opciones_pedido()).order_by(Pedido.id.desc())
    if mesa is not None:
        query = query.join(Pedido.cuenta).join(Cuenta.mesa).where(Mesa.numero == mesa)
    if solo_mios or usuario.rol == Rol.MESERO:
        query = query.where(Pedido.mesero_id == usuario.id)
    return db.scalars(query).unique().all()


@router.get("/pedidos/mesa/{numero}", response_model=list[PedidoOut])
def listar_pedidos_por_mesa(
    numero: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(roles_pedido),
):
    query = (
        select(Pedido)
        .options(*_opciones_pedido())
        .join(Pedido.cuenta)
        .join(Cuenta.mesa)
        .where(Mesa.numero == numero)
        .order_by(Pedido.id.desc())
    )
    return db.scalars(query).unique().all()


@router.get("/pedidos/{pedido_id}", response_model=PedidoOut)
def obtener_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_pedido),
):
    pedido = _cargar_pedido(db, pedido_id)
    _validar_propietario(pedido, usuario)
    return pedido


@router.put("/pedidos/{pedido_id}", response_model=PedidoOut)
def modificar_pedido(
    pedido_id: int,
    payload: PedidoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_pedido),
):
    pedido = _cargar_pedido(db, pedido_id)
    _validar_propietario(pedido, usuario)
    if not puede_modificarse(pedido) and usuario.rol != Rol.ADMINISTRADOR:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El pedido ya está en preparación; requiere autorización del administrador",
        )

    if payload.mesa_numero != pedido.mesa_numero:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La mesa de un pedido existente no se puede cambiar",
        )

    estaba_confirmado = pedido.confirmado
    reemplazar_lineas(db, pedido, payload.lineas)
    if estaba_confirmado:
        confirmar_pedido(db, pedido)
    return _cargar_pedido(db, pedido_id)


@router.post("/pedidos/{pedido_id}/confirmar", response_model=PedidoOut)
def confirmar(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_pedido),
):
    pedido = _cargar_pedido(db, pedido_id)
    _validar_propietario(pedido, usuario)
    confirmar_pedido(db, pedido)
    return _cargar_pedido(db, pedido_id)


@router.delete("/pedidos/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar(
    pedido_id: int,
    motivo: str = Query(default=""),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_pedido),
):
    pedido = _cargar_pedido(db, pedido_id)
    _validar_propietario(pedido, usuario)
    if not puede_modificarse(pedido) and usuario.rol != Rol.ADMINISTRADOR:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El pedido ya está en preparación; requiere autorización del administrador",
        )
    cancelar_pedido(db, pedido, usuario, motivo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/comandas", response_model=list[ComandaOut])
def listar_comandas(
    area: AreaPreparacion | None = None,
    estado: EstadoComanda | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_comanda),
):
    query = (
        select(Comanda)
        .join(Comanda.pedido)
        .where(Pedido.cancelado_en.is_(None))
        .options(
            selectinload(Comanda.lineas),
            selectinload(Comanda.pedido)
            .selectinload(Pedido.cuenta)
            .selectinload(Cuenta.mesa),
        )
        .order_by(Comanda.id)
    )

    if usuario.rol == Rol.ENCARGADO_AREA:
        area = usuario.area
    elif usuario.rol == Rol.PATINADOR:
        estado = EstadoComanda.LISTO

    if area is not None:
        query = query.where(Comanda.area == area)
    if estado is not None:
        query = query.where(Comanda.estado == estado)
    return db.scalars(query).unique().all()


@router.put("/comandas/{comanda_id}/estado", response_model=ComandaOut)
def actualizar_estado(
    comanda_id: int,
    payload: EstadoComandaIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_estado),
):
    comanda = _cargar_comanda(db, comanda_id)
    if usuario.rol == Rol.ENCARGADO_AREA and comanda.area != usuario.area:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La comanda pertenece a otra área"
        )

    try:
        cambiar_estado_comanda(db, comanda, payload.estado)
    except DomainError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    return _cargar_comanda(db, comanda_id)


@router.post("/comandas/{comanda_id}/entregar", response_model=ComandaOut)
def entregar(
    comanda_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_entrega),
):
    comanda = _cargar_comanda(db, comanda_id)
    if usuario.rol == Rol.MESERO and comanda.pedido.mesero_id != usuario.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La comanda pertenece a otro mesero"
        )
    try:
        cambiar_estado_comanda(db, comanda, EstadoComanda.ENTREGADO)
    except DomainError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    return _cargar_comanda(db, comanda_id)


@router.post("/comandas/{comanda_id}/imprimir", response_model=ComandaOut)
def reimprimir_comanda(
    comanda_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_impresion),
):
    comanda = _cargar_comanda(db, comanda_id)
    if usuario.rol == Rol.ENCARGADO_AREA and comanda.area != usuario.area:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La comanda pertenece a otra área"
        )
    try:
        imprimir_comanda(comanda)
        db.commit()
    except OSError as exc:
        logger.exception("Error al imprimir comanda %s", comanda_id)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "No se pudo escribir el archivo de impresión",
        ) from exc

    evento_bus.publicar(
        {
            "tipo": "comanda_impresa",
            "comanda_id": comanda.id,
            "area": comanda.area.value,
            "archivo": comanda.archivo_impresion,
            "mesero_id": comanda.pedido.mesero_id,
        }
    )
    return _cargar_comanda(db, comanda_id)


@router.get("/comandas/{comanda_id}/ticket")
def descargar_ticket(
    comanda_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(roles_impresion),
):
    comanda = _cargar_comanda(db, comanda_id)
    if usuario.rol == Rol.ENCARGADO_AREA and comanda.area != usuario.area:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La comanda pertenece a otra área"
        )
    ruta = ruta_archivo(comanda)
    if ruta is None or not ruta.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket no disponible")
    return FileResponse(ruta, media_type="text/plain", filename=ruta.name)
