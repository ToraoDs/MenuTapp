import logging
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .events import evento_bus
from .impresion import imprimir_comanda
from .models import (
    AreaPreparacion,
    Comanda,
    Cuenta,
    EstadoComanda,
    EstadoCuenta,
    LineaPedido,
    Mesa,
    MetodoPago,
    Opcion,
    Pago,
    Pedido,
    Producto,
    Usuario,
    utcnow,
)
from .schemas import LineaIn

logger = logging.getLogger(__name__)


class DomainError(Exception):
    pass


def _publicar(tipo: str, **datos) -> None:
    evento_bus.publicar({"tipo": tipo, **datos})


def construir_linea(db: Session, data: LineaIn) -> LineaPedido:
    if data.producto_id is None:
        return LineaPedido(
            producto_id=None,
            nombre=(data.nombre or "").strip(),
            cantidad=data.cantidad,
            precio_unitario=data.precio_unitario,
            observacion=data.observacion.strip(),
            opciones=[],
            area=data.area,
        )

    producto = db.get(Producto, data.producto_id)
    if producto is None or not producto.activo:
        raise DomainError(f"El producto {data.producto_id} no existe o está inactivo")
    if producto.categoria is None or not producto.categoria.activo:
        raise DomainError("La categoría del producto está inactiva")

    grupos = {grupo.id: grupo for grupo in producto.grupos if grupo.activo}
    disponibles: dict[int, Opcion] = {
        opcion.id: opcion
        for grupo in grupos.values()
        for opcion in grupo.opciones
        if opcion.activo
    }

    if len(set(data.opcion_ids)) != len(data.opcion_ids):
        raise DomainError("No se puede repetir una opción")

    elegidas: list[Opcion] = []
    for opcion_id in data.opcion_ids:
        opcion = disponibles.get(opcion_id)
        if opcion is None:
            raise DomainError(
                f"La opción {opcion_id} no corresponde a «{producto.nombre}»"
            )
        elegidas.append(opcion)

    por_grupo = Counter(opcion.grupo_id for opcion in elegidas)
    for grupo_id, cantidad in por_grupo.items():
        grupo = grupos[grupo_id]
        if cantidad > grupo.max_opciones:
            raise DomainError(
                f"«{grupo.titulo}» permite máximo {grupo.max_opciones} opción(es)"
            )

    return LineaPedido(
        producto_id=producto.id,
        nombre=producto.nombre,
        cantidad=data.cantidad,
        precio_unitario=producto.precio + sum(opcion.precio for opcion in elegidas),
        observacion=data.observacion.strip(),
        opciones=[opcion.nombre for opcion in elegidas],
        area=producto.categoria.area,
    )


def obtener_o_crear_cuenta(db: Session, mesa: Mesa) -> Cuenta:
    cuenta = db.scalar(
        select(Cuenta).where(
            Cuenta.mesa_id == mesa.id, Cuenta.estado == EstadoCuenta.ABIERTA
        )
    )
    if cuenta is None:
        cuenta = Cuenta(mesa=mesa)
        db.add(cuenta)
        db.flush()
    return cuenta


def crear_pedido(db: Session, data, mesero: Usuario) -> Pedido:
    mesa = db.scalar(select(Mesa).where(Mesa.numero == data.mesa_numero))
    if mesa is None or not mesa.activa:
        raise DomainError(f"La mesa {data.mesa_numero} no existe o está inactiva")

    lineas = [construir_linea(db, linea) for linea in data.lineas]
    cuenta = obtener_o_crear_cuenta(db, mesa)
    pedido = Pedido(cuenta=cuenta, mesero=mesero, lineas=lineas)
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    _publicar(
        "pedido_creado",
        pedido_id=pedido.id,
        cuenta_id=cuenta.id,
        mesa_numero=mesa.numero,
        mesero_id=mesero.id,
    )
    return pedido


def puede_modificarse(pedido: Pedido) -> bool:
    if pedido.cancelado_en is not None:
        return False
    if pedido.cuenta.estado != EstadoCuenta.ABIERTA:
        return False
    return not pedido.comandas or all(
        comanda.estado == EstadoComanda.PENDIENTE for comanda in pedido.comandas
    )


def confirmar_pedido(db: Session, pedido: Pedido) -> Pedido:
    if pedido.cancelado_en is not None:
        raise DomainError("No se puede confirmar un pedido cancelado")
    if pedido.cuenta.estado != EstadoCuenta.ABIERTA:
        raise DomainError("La cuenta ya está cerrada")
    if pedido.comandas:
        raise DomainError("El pedido ya fue confirmado")
    if not pedido.lineas:
        raise DomainError("El pedido no tiene líneas")

    por_area: dict[AreaPreparacion, list[LineaPedido]] = {}
    for linea in pedido.lineas:
        por_area.setdefault(linea.area, []).append(linea)

    for area, lineas in por_area.items():
        comanda = Comanda(
            pedido=pedido,
            area=area,
            estado=EstadoComanda.PENDIENTE,
            recibida_en=utcnow(),
        )
        for linea in lineas:
            linea.comanda = comanda
        db.add(comanda)

    db.commit()
    db.refresh(pedido)

    for comanda in pedido.comandas:
        try:
            imprimir_comanda(comanda)
            _publicar(
                "comanda_impresa",
                comanda_id=comanda.id,
                area=comanda.area.value,
                archivo=comanda.archivo_impresion,
                mesero_id=pedido.mesero_id,
            )
        except OSError:
            logger.exception("No se pudo imprimir la comanda %s", comanda.id)
    db.commit()

    _publicar(
        "pedido_confirmado",
        pedido_id=pedido.id,
        cuenta_id=pedido.cuenta_id,
        mesa_numero=pedido.mesa_numero,
        mesero_id=pedido.mesero_id,
    )
    for comanda in pedido.comandas:
        _publicar(
            "comanda_creada",
            comanda_id=comanda.id,
            pedido_id=pedido.id,
            area=comanda.area.value,
            mesa_numero=pedido.mesa_numero,
            estado=comanda.estado.value,
            mesero_id=pedido.mesero_id,
        )
    db.refresh(pedido)
    return pedido


def reemplazar_lineas(db: Session, pedido: Pedido, lineas: list[LineaIn]) -> Pedido:
    if pedido.cancelado_en is not None:
        raise DomainError("No se puede modificar un pedido cancelado")
    if pedido.cuenta.estado != EstadoCuenta.ABIERTA:
        raise DomainError("No se puede modificar un pedido de una cuenta pagada")
    pedido.comandas.clear()
    pedido.lineas.clear()
    db.flush()
    pedido.lineas = [construir_linea(db, linea) for linea in lineas]
    db.commit()
    db.refresh(pedido)
    return pedido


def cancelar_pedido(
    db: Session, pedido: Pedido, usuario: Usuario, motivo: str = ""
) -> None:
    if pedido.cancelado_en is not None:
        raise DomainError("El pedido ya está cancelado")
    if pedido.cuenta.estado != EstadoCuenta.ABIERTA:
        raise DomainError("No se puede cancelar un pedido de una cuenta pagada")

    pedido.cancelado_en = utcnow()
    pedido.cancelado_por_id = usuario.id
    pedido.motivo_cancelacion = motivo.strip()
    db.commit()
    _publicar(
        "pedido_cancelado",
        pedido_id=pedido.id,
        cuenta_id=pedido.cuenta_id,
        mesa_numero=pedido.mesa_numero,
        mesero_id=pedido.mesero_id,
        cancelado_por_id=usuario.id,
    )


def cambiar_estado_comanda(
    db: Session, comanda: Comanda, nuevo: EstadoComanda
) -> Comanda:
    if comanda.pedido.cancelado_en is not None:
        raise DomainError("La comanda pertenece a un pedido cancelado")

    transiciones = {
        EstadoComanda.PENDIENTE: {EstadoComanda.EN_PREPARACION},
        EstadoComanda.EN_PREPARACION: {EstadoComanda.LISTO},
        EstadoComanda.LISTO: {EstadoComanda.ENTREGADO},
        EstadoComanda.ENTREGADO: set(),
    }
    if nuevo not in transiciones[comanda.estado]:
        raise DomainError(
            f"No se puede pasar de {comanda.estado.value} a {nuevo.value}"
        )

    comanda.estado = nuevo
    if nuevo == EstadoComanda.EN_PREPARACION:
        comanda.en_preparacion_en = utcnow()
    if nuevo == EstadoComanda.LISTO:
        comanda.lista_en = utcnow()
    if nuevo == EstadoComanda.ENTREGADO:
        comanda.entregada_en = utcnow()
    db.commit()
    db.refresh(comanda)

    _publicar(
        "comanda_estado",
        comanda_id=comanda.id,
        pedido_id=comanda.pedido_id,
        area=comanda.area.value,
        estado=comanda.estado.value,
        mesa_numero=comanda.mesa_numero,
        mesero_id=comanda.pedido.mesero_id,
    )
    if nuevo == EstadoComanda.ENTREGADO:
        _publicar(
            "comanda_entregada",
            comanda_id=comanda.id,
            pedido_id=comanda.pedido_id,
            area=comanda.area.value,
            mesa_numero=comanda.mesa_numero,
            mesero_id=comanda.pedido.mesero_id,
        )
    return comanda


def enviar_cuenta_a_caja(db: Session, cuenta: Cuenta) -> Cuenta:
    if cuenta.estado != EstadoCuenta.ABIERTA:
        raise DomainError("La cuenta ya está cerrada")

    activos = [pedido for pedido in cuenta.pedidos if pedido.cancelado_en is None]
    if not activos:
        raise DomainError("La cuenta no tiene pedidos")
    if any(not pedido.confirmado for pedido in activos):
        raise DomainError("Hay pedidos sin confirmar en la mesa")

    if cuenta.enviada_caja_en is None:
        cuenta.enviada_caja_en = utcnow()
        db.commit()
        db.refresh(cuenta)
        _publicar(
            "cuenta_enviada_caja",
            cuenta_id=cuenta.id,
            mesa_numero=cuenta.mesa_numero,
            total=cuenta.total,
        )
    return cuenta


def registrar_pago(
    db: Session, cuenta: Cuenta, metodo: MetodoPago, valor: int
) -> Pago:
    if cuenta.estado != EstadoCuenta.ABIERTA:
        raise DomainError("La cuenta ya está cerrada")
    if cuenta.pago is not None:
        raise DomainError("La cuenta ya tiene un pago registrado")

    activos = [pedido for pedido in cuenta.pedidos if pedido.cancelado_en is None]
    if not activos:
        raise DomainError("La cuenta no tiene productos")
    if any(not pedido.confirmado for pedido in activos):
        raise DomainError("Hay pedidos sin confirmar en la mesa")

    total = sum(pedido.total for pedido in activos)
    if total <= 0:
        raise DomainError("La cuenta no tiene productos")
    if valor < total:
        raise DomainError(f"El valor recibido no cubre el total de {total}")

    pago = Pago(
        cuenta=cuenta,
        metodo=metodo,
        valor=valor,
        cambio=valor - total,
        numero_recibo=f"REC-{cuenta.id:06d}",
    )
    cuenta.estado = EstadoCuenta.PAGADA
    cuenta.cerrada_en = utcnow()
    cuenta.total_cobrado = total
    db.add(pago)
    db.commit()
    db.refresh(pago)
    _publicar(
        "cuenta_pagada",
        cuenta_id=cuenta.id,
        mesa_numero=cuenta.mesa_numero,
        total=total,
        metodo=metodo.value,
        numero_recibo=pago.numero_recibo,
    )
    return pago
