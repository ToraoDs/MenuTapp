import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload, with_loader_criteria

from ..database import get_db
from ..events import evento_bus
from ..models import (
    AreaPreparacion,
    Categoria,
    GrupoOpciones,
    Mesa,
    Opcion,
    Pedido,
    Cuenta,
    Producto,
    ProductoGrupoOpciones,
    Rol,
    Usuario,
)
from ..schemas import (
    CategoriaIn,
    CategoriaOut,
    CategoriaUpdate,
    GrupoOpcionesIn,
    GrupoOpcionesOut,
    GrupoOpcionesUpdate,
    MesaIn,
    MesaOut,
    MesaUpdate,
    MesasGenerarIn,
    MesasGenerarOut,
    OpcionIn,
    OpcionOut,
    OpcionUpdate,
    ProductoIn,
    ProductoOut,
    ProductoUpdate,
    ProductoGruposIn,
)
from ..security import requiere_roles, usuario_actual

router = APIRouter(prefix="/api", tags=["menu"])
logger = logging.getLogger(__name__)
solo_admin = requiere_roles(Rol.ADMINISTRADOR)


def _no_encontrado(recurso: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{recurso} no encontrado")


def _categoria(db: Session, categoria_id: int) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise _no_encontrado("Categoría")
    return categoria


def _producto(db: Session, producto_id: int) -> Producto:
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise _no_encontrado("Producto")
    return producto


def _grupo(db: Session, grupo_id: int) -> GrupoOpciones:
    grupo = db.get(GrupoOpciones, grupo_id)
    if grupo is None:
        raise _no_encontrado("Grupo de opciones")
    return grupo


def _opcion(db: Session, opcion_id: int) -> Opcion:
    opcion = db.get(Opcion, opcion_id)
    if opcion is None:
        raise _no_encontrado("Opción")
    return opcion


def _publicar_menu(accion: str, **datos) -> None:
    evento_bus.publicar({"tipo": "menu_actualizado", "accion": accion, **datos})


def _publicar_mesa(accion: str, mesa: Mesa) -> None:
    evento_bus.publicar(
        {
            "tipo": "mesa_actualizada",
            "accion": accion,
            "mesa_id": mesa.id,
            "numero": mesa.numero,
            "activa": mesa.activa,
        }
    )


def _asignar_grupos(db: Session, producto: Producto, grupo_ids: list[int]) -> None:
    ids: list[int] = []
    for grupo_id in grupo_ids:
        if grupo_id not in ids:
            ids.append(grupo_id)

    grupos = list(db.scalars(select(GrupoOpciones).where(GrupoOpciones.id.in_(ids))))
    if len(grupos) != len(ids):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Uno o más grupos de opciones no existen",
        )
    if any(not grupo.activo for grupo in grupos):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "No se puede asignar un grupo inactivo",
        )

    por_id = {grupo.id: grupo for grupo in grupos}
    producto.option_links.clear()
    db.flush()
    producto.option_links = [
        ProductoGrupoOpciones(grupo=por_id[grupo_id], posicion=indice)
        for indice, grupo_id in enumerate(ids)
    ]


@router.get("/menu", response_model=list[CategoriaOut])
def obtener_menu(
    area: AreaPreparacion | None = Query(default=None),
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    if incluir_inactivos and usuario.rol != Rol.ADMINISTRADOR:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso denegado")

    query = (
        select(Categoria)
        .options(
            selectinload(Categoria.productos)
            .selectinload(Producto.option_links)
            .selectinload(ProductoGrupoOpciones.grupo)
            .selectinload(GrupoOpciones.opciones)
        )
        .order_by(Categoria.posicion, Categoria.id)
    )
    if area is not None:
        query = query.where(Categoria.area == area)

    if not incluir_inactivos:
        query = query.where(Categoria.activo.is_(True)).options(
            with_loader_criteria(Producto, Producto.activo.is_(True)),
            with_loader_criteria(GrupoOpciones, GrupoOpciones.activo.is_(True)),
            with_loader_criteria(Opcion, Opcion.activo.is_(True)),
        )

    return db.scalars(query).unique().all()


@router.get("/mesas", response_model=list[MesaOut])
def listar_mesas(
    incluir_inactivas: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    if incluir_inactivas and usuario.rol != Rol.ADMINISTRADOR:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso denegado")

    query = (
        select(Mesa)
        .options(
            selectinload(Mesa.cuentas)
            .selectinload(Cuenta.pedidos)
            .selectinload(Pedido.lineas)
        )
        .order_by(Mesa.numero)
    )
    if not incluir_inactivas:
        query = query.where(Mesa.activa.is_(True))
    return db.scalars(query).unique().all()


# --- Administración de menú -------------------------------------------------


@router.post(
    "/menu/categorias",
    response_model=CategoriaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(solo_admin)],
)
def crear_categoria(payload: CategoriaIn, db: Session = Depends(get_db)):
    categoria = Categoria(**payload.model_dump())
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    _publicar_menu("categoria_creada", categoria_id=categoria.id)
    return categoria


@router.put(
    "/menu/categorias/{categoria_id}",
    response_model=CategoriaOut,
    dependencies=[Depends(solo_admin)],
)
def actualizar_categoria(
    categoria_id: int, payload: CategoriaUpdate, db: Session = Depends(get_db)
):
    categoria = _categoria(db, categoria_id)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(categoria, campo, valor)
    db.commit()
    db.refresh(categoria)
    _publicar_menu("categoria_actualizada", categoria_id=categoria.id)
    return categoria


@router.delete(
    "/menu/categorias/{categoria_id}",
    dependencies=[Depends(solo_admin)],
)
def desactivar_categoria(
    categoria_id: int,
    cascade: bool = False,
    db: Session = Depends(get_db),
):
    categoria = _categoria(db, categoria_id)
    activos = [producto for producto in categoria.productos if producto.activo]
    if activos and not cascade:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La categoría tiene productos activos; use cascade=true",
        )
    categoria.activo = False
    if cascade:
        for producto in activos:
            producto.activo = False
    db.commit()
    _publicar_menu("categoria_desactivada", categoria_id=categoria.id)
    return {"ok": True}


@router.post(
    "/menu/categorias/{categoria_id}/productos",
    response_model=ProductoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(solo_admin)],
)
def crear_producto(
    categoria_id: int, payload: ProductoIn, db: Session = Depends(get_db)
):
    categoria = _categoria(db, categoria_id)
    if not categoria.activo:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "No se puede agregar productos a una categoría inactiva",
        )
    datos = payload.model_dump(exclude={"grupo_ids"})
    datos["categoria_id"] = categoria_id
    producto = Producto(**datos)
    db.add(producto)
    db.flush()
    _asignar_grupos(db, producto, payload.grupo_ids)
    db.commit()
    db.refresh(producto)
    _publicar_menu("producto_creado", producto_id=producto.id)
    return producto


@router.put(
    "/menu/productos/{producto_id}",
    response_model=ProductoOut,
    dependencies=[Depends(solo_admin)],
)
def actualizar_producto(
    producto_id: int, payload: ProductoUpdate, db: Session = Depends(get_db)
):
    producto = _producto(db, producto_id)
    datos = payload.model_dump(exclude_unset=True)
    grupo_ids = datos.pop("grupo_ids", None)

    categoria_id = datos.get("categoria_id")
    if categoria_id is not None:
        categoria = _categoria(db, categoria_id)
        if not categoria.activo:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "No se puede mover el producto a una categoría inactiva",
            )

    for campo, valor in datos.items():
        setattr(producto, campo, valor)
    if grupo_ids is not None:
        _asignar_grupos(db, producto, grupo_ids)
    db.commit()
    db.refresh(producto)
    _publicar_menu("producto_actualizado", producto_id=producto.id)
    return producto


@router.delete(
    "/menu/productos/{producto_id}",
    dependencies=[Depends(solo_admin)],
)
def desactivar_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = _producto(db, producto_id)
    producto.activo = False
    db.commit()
    _publicar_menu("producto_desactivado", producto_id=producto.id)
    return {"ok": True}


@router.put(
    "/menu/productos/{producto_id}/grupos",
    response_model=ProductoOut,
    dependencies=[Depends(solo_admin)],
)
def asignar_grupos(
    producto_id: int, payload: ProductoGruposIn, db: Session = Depends(get_db)
):
    producto = _producto(db, producto_id)
    _asignar_grupos(db, producto, payload.grupo_ids)
    db.commit()
    db.refresh(producto)
    _publicar_menu("producto_grupos_actualizados", producto_id=producto.id)
    return producto


@router.get("/menu/grupos", response_model=list[GrupoOpcionesOut])
def listar_grupos(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    if incluir_inactivos and usuario.rol != Rol.ADMINISTRADOR:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso denegado")

    query = (
        select(GrupoOpciones)
        .options(selectinload(GrupoOpciones.opciones))
        .order_by(GrupoOpciones.titulo, GrupoOpciones.id)
    )
    if not incluir_inactivos:
        query = query.where(GrupoOpciones.activo.is_(True)).options(
            with_loader_criteria(Opcion, Opcion.activo.is_(True))
        )
    return db.scalars(query).unique().all()


@router.get("/menu/grupos/{grupo_id}", response_model=GrupoOpcionesOut)
def obtener_grupo(
    grupo_id: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(usuario_actual),
):
    grupo = db.scalar(
        select(GrupoOpciones)
        .where(GrupoOpciones.id == grupo_id)
        .options(selectinload(GrupoOpciones.opciones))
    )
    if grupo is None:
        raise _no_encontrado("Grupo de opciones")
    return grupo


@router.post(
    "/menu/grupos",
    response_model=GrupoOpcionesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(solo_admin)],
)
def crear_grupo(payload: GrupoOpcionesIn, db: Session = Depends(get_db)):
    grupo = GrupoOpciones(**payload.model_dump())
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    _publicar_menu("grupo_creado", grupo_id=grupo.id)
    return grupo


@router.put(
    "/menu/grupos/{grupo_id}",
    response_model=GrupoOpcionesOut,
    dependencies=[Depends(solo_admin)],
)
def actualizar_grupo(
    grupo_id: int, payload: GrupoOpcionesUpdate, db: Session = Depends(get_db)
):
    grupo = _grupo(db, grupo_id)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(grupo, campo, valor)
    db.commit()
    db.refresh(grupo)
    _publicar_menu("grupo_actualizado", grupo_id=grupo.id)
    return grupo


@router.delete(
    "/menu/grupos/{grupo_id}",
    dependencies=[Depends(solo_admin)],
)
def desactivar_grupo(
    grupo_id: int,
    desvincular: bool = False,
    db: Session = Depends(get_db),
):
    grupo = _grupo(db, grupo_id)
    en_uso = db.scalar(
        select(func.count())
        .select_from(ProductoGrupoOpciones)
        .join(Producto, Producto.id == ProductoGrupoOpciones.producto_id)
        .where(
            ProductoGrupoOpciones.grupo_id == grupo_id,
            Producto.activo.is_(True),
        )
    )
    if en_uso and not desvincular:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El grupo está en uso; use desvincular=true",
        )
    if desvincular:
        db.execute(
            delete(ProductoGrupoOpciones).where(
                ProductoGrupoOpciones.grupo_id == grupo_id
            )
        )
    grupo.activo = False
    db.commit()
    _publicar_menu("grupo_desactivado", grupo_id=grupo.id)
    return {"ok": True}


@router.post(
    "/menu/grupos/{grupo_id}/opciones",
    response_model=OpcionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(solo_admin)],
)
def crear_opcion(
    grupo_id: int, payload: OpcionIn, db: Session = Depends(get_db)
):
    grupo = _grupo(db, grupo_id)
    if not grupo.activo:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "No se puede agregar opciones a un grupo inactivo",
        )
    opcion = Opcion(grupo=grupo, **payload.model_dump())
    db.add(opcion)
    db.commit()
    db.refresh(opcion)
    _publicar_menu("opcion_creada", opcion_id=opcion.id)
    return opcion


@router.put(
    "/menu/opciones/{opcion_id}",
    response_model=OpcionOut,
    dependencies=[Depends(solo_admin)],
)
def actualizar_opcion(
    opcion_id: int, payload: OpcionUpdate, db: Session = Depends(get_db)
):
    opcion = _opcion(db, opcion_id)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(opcion, campo, valor)
    db.commit()
    db.refresh(opcion)
    _publicar_menu("opcion_actualizada", opcion_id=opcion.id)
    return opcion


@router.delete(
    "/menu/opciones/{opcion_id}",
    dependencies=[Depends(solo_admin)],
)
def desactivar_opcion(opcion_id: int, db: Session = Depends(get_db)):
    opcion = _opcion(db, opcion_id)
    opcion.activo = False
    db.commit()
    _publicar_menu("opcion_desactivada", opcion_id=opcion.id)
    return {"ok": True}


# --- Administración de mesas ------------------------------------------------


@router.post(
    "/mesas",
    response_model=MesaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(solo_admin)],
)
def crear_mesa(payload: MesaIn, db: Session = Depends(get_db)):
    if db.scalar(select(Mesa).where(Mesa.numero == payload.numero)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El número de mesa ya existe")
    mesa = Mesa(**payload.model_dump())
    db.add(mesa)
    db.commit()
    db.refresh(mesa)
    _publicar_mesa("creada", mesa)
    return mesa


@router.post(
    "/mesas/generar",
    response_model=MesasGenerarOut,
    dependencies=[Depends(solo_admin)],
)
def generar_mesas(payload: MesasGenerarIn, db: Session = Depends(get_db)):
    existentes = set(
        db.scalars(
            select(Mesa.numero).where(
                Mesa.numero >= payload.desde, Mesa.numero <= payload.hasta
            )
        )
    )
    creadas: list[int] = []
    for numero in range(payload.desde, payload.hasta + 1):
        if numero not in existentes:
            db.add(Mesa(numero=numero))
            creadas.append(numero)

    db.commit()
    if creadas:
        evento_bus.publicar(
            {
                "tipo": "mesa_actualizada",
                "accion": "generadas",
                "numeros": creadas,
            }
        )
    return MesasGenerarOut(
        creadas=creadas,
        existentes=sorted(existentes),
    )


@router.put(
    "/mesas/{mesa_id}",
    response_model=MesaOut,
    dependencies=[Depends(solo_admin)],
)
def actualizar_mesa(
    mesa_id: int, payload: MesaUpdate, db: Session = Depends(get_db)
):
    mesa = db.get(Mesa, mesa_id)
    if mesa is None:
        raise _no_encontrado("Mesa")

    datos = payload.model_dump(exclude_unset=True)
    nuevo_numero = datos.get("numero")
    if nuevo_numero is not None and nuevo_numero != mesa.numero:
        if db.scalar(select(Mesa).where(Mesa.numero == nuevo_numero)) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "El número de mesa ya existe")

    if datos.get("activa") is False and mesa.cuenta_abierta:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede desactivar una mesa con cuenta abierta",
        )

    for campo, valor in datos.items():
        setattr(mesa, campo, valor)
    db.commit()
    db.refresh(mesa)
    _publicar_mesa("actualizada", mesa)
    return mesa


@router.delete(
    "/mesas/{mesa_id}",
    dependencies=[Depends(solo_admin)],
)
def desactivar_mesa(mesa_id: int, db: Session = Depends(get_db)):
    mesa = db.get(Mesa, mesa_id)
    if mesa is None:
        raise _no_encontrado("Mesa")
    if mesa.cuenta_abierta:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede desactivar una mesa con cuenta abierta",
        )
    mesa.activa = False
    db.commit()
    _publicar_mesa("desactivada", mesa)
    return {"ok": True}
