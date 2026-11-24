from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import (
    AreaPreparacion,
    EstadoComanda,
    EstadoCuenta,
    EstadoPedido,
    MetodoPago,
    Rol,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    usuario: str
    contrasena: str


class UsuarioOut(ORMModel):
    id: int
    nombre: str
    usuario: str
    rol: Rol
    area: AreaPreparacion | None
    activo: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


class EventoTokenOut(BaseModel):
    token: str
    token_type: str = "sse"
    expira_en_segundos: int


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    usuario: str = Field(min_length=3, max_length=60)
    contrasena: str = Field(min_length=4, max_length=100)
    rol: Rol
    area: AreaPreparacion | None = None
    activo: bool = True

    @model_validator(mode="after")
    def area_coherente(self):
        if self.rol == Rol.ENCARGADO_AREA and self.area is None:
            raise ValueError("Un encargado de área requiere un área")
        if self.rol != Rol.ENCARGADO_AREA and self.area is not None:
            raise ValueError("Solo los encargados de área tienen área")
        return self


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    rol: Rol | None = None
    area: AreaPreparacion | None = None
    activo: bool | None = None
    contrasena: str | None = Field(default=None, min_length=4, max_length=100)


class OpcionOut(ORMModel):
    id: int
    nombre: str
    precio: int
    posicion: int
    activo: bool


class GrupoOpcionesOut(ORMModel):
    id: int
    titulo: str
    max_opciones: int
    activo: bool
    opciones: list[OpcionOut]


class ProductoOut(ORMModel):
    id: int
    categoria_id: int
    nombre: str
    precio: int
    descripcion: str
    posicion: int
    activo: bool
    grupos: list[GrupoOpcionesOut]


class CategoriaOut(ORMModel):
    id: int
    nombre: str
    area: AreaPreparacion
    emoji: str
    hue: int
    posicion: int
    activo: bool
    productos: list[ProductoOut]


class MesaOut(ORMModel):
    id: int
    numero: int
    activa: bool
    cuenta_abierta: bool
    cuenta_id: int | None
    total_actual: int
    enviada_caja: bool


class MesaIn(BaseModel):
    numero: int = Field(gt=0)
    activa: bool = True


class MesaUpdate(BaseModel):
    numero: int | None = Field(default=None, gt=0)
    activa: bool | None = None


class MesasGenerarIn(BaseModel):
    desde: int = Field(ge=1)
    hasta: int = Field(ge=1)

    @model_validator(mode="after")
    def rango_valido(self):
        if self.hasta < self.desde:
            raise ValueError("El rango de mesas es inválido")
        if self.hasta - self.desde > 500:
            raise ValueError("El rango de mesas es demasiado grande")
        return self


class MesasGenerarOut(BaseModel):
    creadas: list[int]
    existentes: list[int]


class CategoriaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    area: AreaPreparacion
    emoji: str = Field(default="", max_length=8)
    hue: int = Field(default=0, ge=0, le=360)
    posicion: int = Field(default=0, ge=0)
    activo: bool = True


class CategoriaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    area: AreaPreparacion | None = None
    emoji: str | None = Field(default=None, max_length=8)
    hue: int | None = Field(default=None, ge=0, le=360)
    posicion: int | None = Field(default=None, ge=0)
    activo: bool | None = None


class ProductoIn(BaseModel):
    categoria_id: int | None = None
    nombre: str = Field(min_length=1, max_length=120)
    precio: int = Field(ge=0)
    descripcion: str = Field(default="", max_length=500)
    posicion: int = Field(default=0, ge=0)
    activo: bool = True
    grupo_ids: list[int] = Field(default_factory=list)


class ProductoUpdate(BaseModel):
    categoria_id: int | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    precio: int | None = Field(default=None, ge=0)
    descripcion: str | None = Field(default=None, max_length=500)
    posicion: int | None = Field(default=None, ge=0)
    activo: bool | None = None
    grupo_ids: list[int] | None = None


class ProductoGruposIn(BaseModel):
    grupo_ids: list[int] = Field(default_factory=list)


class GrupoOpcionesIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=80)
    max_opciones: int = Field(default=1, ge=1, le=20)
    activo: bool = True


class GrupoOpcionesUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=80)
    max_opciones: int | None = Field(default=None, ge=1, le=20)
    activo: bool | None = None


class OpcionIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    precio: int = Field(default=0, ge=0)
    posicion: int = Field(default=0, ge=0)
    activo: bool = True


class OpcionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    precio: int | None = Field(default=None, ge=0)
    posicion: int | None = Field(default=None, ge=0)
    activo: bool | None = None


class LineaIn(BaseModel):
    producto_id: int | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    precio_unitario: int | None = Field(default=None, gt=0)
    cantidad: int = Field(default=1, ge=1, le=99)
    observacion: str = Field(default="", max_length=500)
    opcion_ids: list[int] = Field(default_factory=list)
    area: AreaPreparacion | None = None

    @model_validator(mode="after")
    def producto_libre_completo(self):
        if self.producto_id is None and (
            not self.nombre or self.precio_unitario is None or self.area is None
        ):
            raise ValueError(
                "Un producto libre requiere nombre, precio_unitario y area"
            )
        return self


class LineaOut(ORMModel):
    id: int
    producto_id: int | None
    nombre: str
    cantidad: int
    precio_unitario: int
    observacion: str
    opciones: list[str]
    area: AreaPreparacion
    subtotal: int


class ComandaOut(ORMModel):
    id: int
    pedido_id: int
    mesa_numero: int
    area: AreaPreparacion
    estado: EstadoComanda
    recibida_en: datetime
    en_preparacion_en: datetime | None
    lista_en: datetime | None
    entregada_en: datetime | None
    impresa_en: datetime | None
    archivo_impresion: str | None
    lineas: list[LineaOut]


class PedidoOut(ORMModel):
    id: int
    cuenta_id: int
    mesa_numero: int
    mesero: UsuarioOut
    creado_en: datetime
    confirmado: bool
    estado: EstadoPedido
    cancelado_en: datetime | None
    motivo_cancelacion: str
    total: int
    lineas: list[LineaOut]
    comandas: list[ComandaOut]


class PedidoIn(BaseModel):
    mesa_numero: int = Field(gt=0)
    lineas: list[LineaIn] = Field(min_length=1)


class EstadoComandaIn(BaseModel):
    estado: EstadoComanda


class PagoIn(BaseModel):
    metodo: MetodoPago
    valor: int = Field(ge=0)


class PagoOut(ORMModel):
    id: int
    metodo: MetodoPago
    valor: int
    cambio: int
    pagado_en: datetime
    numero_recibo: str


class CuentaOut(ORMModel):
    id: int
    mesa_numero: int
    abierta_en: datetime
    estado: EstadoCuenta
    cerrada_en: datetime | None
    enviada_caja_en: datetime | None
    total: int
    total_cobrado: int | None
    pedidos: list[PedidoOut]
    pago: PagoOut | None


class ReciboOut(BaseModel):
    numero_recibo: str
    cuenta_id: int
    mesa_numero: int
    cerrada_en: datetime
    lineas: list[LineaOut]
    total: int
    metodo: MetodoPago
    valor: int
    cambio: int


class VentaMetodoOut(BaseModel):
    metodo: MetodoPago
    total: int
    cuentas: int


class VentaDiaOut(BaseModel):
    fecha: str
    total: int
    cuentas: int


class VentaAreaOut(BaseModel):
    area: AreaPreparacion
    total: int
    cantidad: int


class ProductoVendidoOut(BaseModel):
    producto_id: int | None
    producto: str
    cantidad: int
    total: int


class ReporteVentasOut(BaseModel):
    desde: str
    hasta: str
    zona_horaria: str
    total_ventas: int
    cuentas_pagadas: int
    ticket_promedio: int
    por_metodo: list[VentaMetodoOut]
    por_dia: list[VentaDiaOut]
    por_area: list[VentaAreaOut]
    top_productos: list[ProductoVendidoOut]


class ReporteProductosOut(BaseModel):
    desde: str
    hasta: str
    zona_horaria: str
    productos: list[ProductoVendidoOut]
