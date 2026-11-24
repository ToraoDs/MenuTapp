from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    JSON,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Rol(str, Enum):
    MESERO = "MESERO"
    CAJERA = "CAJERA"
    ADMINISTRADOR = "ADMINISTRADOR"
    ENCARGADO_AREA = "ENCARGADO_AREA"
    PATINADOR = "PATINADOR"


class AreaPreparacion(str, Enum):
    PARRILLA = "PARRILLA"
    SOPAS_ENTRADAS = "SOPAS_ENTRADAS"
    BEBIDAS = "BEBIDAS"


class EstadoComanda(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_PREPARACION = "EN_PREPARACION"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"


class EstadoCuenta(str, Enum):
    ABIERTA = "ABIERTA"
    PAGADA = "PAGADA"


class EstadoPedido(str, Enum):
    BORRADOR = "BORRADOR"
    CONFIRMADO = "CONFIRMADO"
    EN_PREPARACION = "EN_PREPARACION"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"
    PAGADO = "PAGADO"
    CANCELADO = "CANCELADO"


class MetodoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"


def enum_column(enum_type):
    return SAEnum(enum_type, native_enum=False, length=30)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    usuario: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[Rol] = mapped_column(enum_column(Rol))
    area: Mapped[AreaPreparacion | None] = mapped_column(enum_column(AreaPreparacion), default=None)
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(default=utcnow)

    pedidos: Mapped[list["Pedido"]] = relationship(
        back_populates="mesero", foreign_keys="Pedido.mesero_id"
    )


class Mesa(Base):
    __tablename__ = "mesas"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(unique=True, index=True)
    activa: Mapped[bool] = mapped_column(default=True)

    cuentas: Mapped[list["Cuenta"]] = relationship(
        back_populates="mesa", order_by="Cuenta.id"
    )

    @property
    def cuenta_abierta_obj(self) -> "Cuenta | None":
        return next(
            (cuenta for cuenta in self.cuentas if cuenta.estado == EstadoCuenta.ABIERTA),
            None,
        )

    @property
    def cuenta_abierta(self) -> bool:
        return self.cuenta_abierta_obj is not None

    @property
    def cuenta_id(self) -> int | None:
        cuenta = self.cuenta_abierta_obj
        return cuenta.id if cuenta is not None else None

    @property
    def total_actual(self) -> int:
        cuenta = self.cuenta_abierta_obj
        return cuenta.total if cuenta is not None else 0

    @property
    def enviada_caja(self) -> bool:
        cuenta = self.cuenta_abierta_obj
        return bool(cuenta and cuenta.enviada_caja_en)


class Cuenta(Base):
    __tablename__ = "cuentas"

    id: Mapped[int] = mapped_column(primary_key=True)
    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesas.id"))
    abierta_en: Mapped[datetime] = mapped_column(default=utcnow)
    estado: Mapped[EstadoCuenta] = mapped_column(
        enum_column(EstadoCuenta), default=EstadoCuenta.ABIERTA
    )
    cerrada_en: Mapped[datetime | None] = mapped_column(default=None)
    enviada_caja_en: Mapped[datetime | None] = mapped_column(default=None)
    total_cobrado: Mapped[int | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_cuenta_abierta_por_mesa",
            "mesa_id",
            unique=True,
            sqlite_where=text("estado = 'ABIERTA'"),
        ),
        Index("ix_cuentas_estado_cerrada_en", "estado", "cerrada_en"),
    )

    mesa: Mapped[Mesa] = relationship(back_populates="cuentas")
    pedidos: Mapped[list["Pedido"]] = relationship(
        back_populates="cuenta", order_by="Pedido.id", cascade="all, delete-orphan"
    )
    pago: Mapped["Pago | None"] = relationship(
        back_populates="cuenta", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def total(self) -> int:
        return sum(
            pedido.total for pedido in self.pedidos if pedido.cancelado_en is None
        )

    @property
    def mesa_numero(self) -> int:
        return self.mesa.numero


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"))
    mesero_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(default=utcnow)
    cancelado_en: Mapped[datetime | None] = mapped_column(default=None)
    cancelado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), default=None
    )
    motivo_cancelacion: Mapped[str] = mapped_column(String(500), default="")

    __table_args__ = (
        Index("ix_pedidos_cuenta_id", "cuenta_id"),
        Index("ix_pedidos_mesero_id", "mesero_id"),
    )

    cuenta: Mapped[Cuenta] = relationship(back_populates="pedidos")
    mesero: Mapped[Usuario] = relationship(
        back_populates="pedidos", foreign_keys=[mesero_id]
    )
    cancelado_por: Mapped[Usuario | None] = relationship(
        foreign_keys=[cancelado_por_id]
    )
    lineas: Mapped[list["LineaPedido"]] = relationship(
        back_populates="pedido", order_by="LineaPedido.id", cascade="all, delete-orphan"
    )
    comandas: Mapped[list["Comanda"]] = relationship(
        back_populates="pedido", order_by="Comanda.id", cascade="all, delete-orphan"
    )

    @property
    def total(self) -> int:
        return sum(linea.subtotal for linea in self.lineas)

    @property
    def confirmado(self) -> bool:
        return bool(self.comandas)

    @property
    def mesa_numero(self) -> int:
        return self.cuenta.mesa_numero

    @property
    def estado(self) -> EstadoPedido:
        if self.cancelado_en is not None:
            return EstadoPedido.CANCELADO
        if self.cuenta is not None and self.cuenta.estado == EstadoCuenta.PAGADA:
            return EstadoPedido.PAGADO
        if not self.comandas:
            return EstadoPedido.BORRADOR

        estados = {comanda.estado for comanda in self.comandas}
        if estados <= {EstadoComanda.ENTREGADO}:
            return EstadoPedido.ENTREGADO
        if estados <= {EstadoComanda.LISTO, EstadoComanda.ENTREGADO}:
            return EstadoPedido.LISTO
        if estados & {
            EstadoComanda.EN_PREPARACION,
            EstadoComanda.LISTO,
            EstadoComanda.ENTREGADO,
        }:
            return EstadoPedido.EN_PREPARACION
        return EstadoPedido.CONFIRMADO


class Comanda(Base):
    __tablename__ = "comandas"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    area: Mapped[AreaPreparacion] = mapped_column(enum_column(AreaPreparacion))
    estado: Mapped[EstadoComanda] = mapped_column(
        enum_column(EstadoComanda), default=EstadoComanda.PENDIENTE
    )
    recibida_en: Mapped[datetime] = mapped_column(default=utcnow)
    en_preparacion_en: Mapped[datetime | None] = mapped_column(default=None)
    lista_en: Mapped[datetime | None] = mapped_column(default=None)
    entregada_en: Mapped[datetime | None] = mapped_column(default=None)
    impresa_en: Mapped[datetime | None] = mapped_column(default=None)
    archivo_impresion: Mapped[str | None] = mapped_column(String(500), default=None)

    __table_args__ = (Index("ix_comandas_area_estado", "area", "estado"),)

    pedido: Mapped[Pedido] = relationship(back_populates="comandas")
    lineas: Mapped[list["LineaPedido"]] = relationship(back_populates="comanda")

    @property
    def mesa_numero(self) -> int:
        return self.pedido.mesa_numero


class LineaPedido(Base):
    __tablename__ = "lineas_pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    comanda_id: Mapped[int | None] = mapped_column(
        ForeignKey("comandas.id", ondelete="SET NULL"), default=None
    )
    producto_id: Mapped[int | None] = mapped_column(
        ForeignKey("productos.id", ondelete="SET NULL"), default=None
    )
    nombre: Mapped[str] = mapped_column(String(120))
    cantidad: Mapped[int]
    precio_unitario: Mapped[int]
    observacion: Mapped[str] = mapped_column(String(500), default="")
    opciones: Mapped[list[str]] = mapped_column(JSON, default=list)
    area: Mapped[AreaPreparacion] = mapped_column(enum_column(AreaPreparacion))

    __table_args__ = (
        Index("ix_lineas_pedido_pedido_id", "pedido_id"),
        Index("ix_lineas_pedido_comanda_id", "comanda_id"),
    )

    pedido: Mapped[Pedido] = relationship(back_populates="lineas")
    comanda: Mapped[Comanda | None] = relationship(back_populates="lineas")

    @property
    def subtotal(self) -> int:
        return self.precio_unitario * self.cantidad


class Pago(Base):
    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"), unique=True)
    metodo: Mapped[MetodoPago] = mapped_column(enum_column(MetodoPago))
    valor: Mapped[int]
    cambio: Mapped[int] = mapped_column(default=0)
    pagado_en: Mapped[datetime] = mapped_column(default=utcnow)
    numero_recibo: Mapped[str] = mapped_column(String(30), unique=True)

    __table_args__ = (Index("ix_pagos_pagado_en", "pagado_en"),)

    cuenta: Mapped[Cuenta] = relationship(back_populates="pago")


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    area: Mapped[AreaPreparacion] = mapped_column(enum_column(AreaPreparacion))
    emoji: Mapped[str] = mapped_column(String(8), default="")
    hue: Mapped[int] = mapped_column(default=0)
    posicion: Mapped[int] = mapped_column(default=0)
    activo: Mapped[bool] = mapped_column(default=True)

    productos: Mapped[list["Producto"]] = relationship(
        back_populates="categoria", order_by="Producto.posicion"
    )


class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    precio: Mapped[int]
    descripcion: Mapped[str] = mapped_column(String(500), default="")
    posicion: Mapped[int] = mapped_column(default=0)
    activo: Mapped[bool] = mapped_column(default=True)

    categoria: Mapped[Categoria] = relationship(back_populates="productos")
    option_links: Mapped[list["ProductoGrupoOpciones"]] = relationship(
        order_by="ProductoGrupoOpciones.posicion", cascade="all, delete-orphan"
    )

    @property
    def grupos(self) -> list["GrupoOpciones"]:
        return [
            link.grupo
            for link in self.option_links
            if link.grupo is not None and link.grupo.activo
        ]


class GrupoOpciones(Base):
    __tablename__ = "grupos_opciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(80))
    max_opciones: Mapped[int] = mapped_column(default=1)
    activo: Mapped[bool] = mapped_column(default=True)

    opciones: Mapped[list["Opcion"]] = relationship(
        back_populates="grupo", order_by="Opcion.posicion", cascade="all, delete-orphan"
    )


class Opcion(Base):
    __tablename__ = "opciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupos_opciones.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    precio: Mapped[int] = mapped_column(default=0)
    posicion: Mapped[int] = mapped_column(default=0)
    activo: Mapped[bool] = mapped_column(default=True)

    grupo: Mapped[GrupoOpciones] = relationship(back_populates="opciones")


class ProductoGrupoOpciones(Base):
    __tablename__ = "producto_grupo_opciones"

    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupos_opciones.id"), primary_key=True)
    posicion: Mapped[int] = mapped_column(default=0)

    grupo: Mapped[GrupoOpciones] = relationship()
