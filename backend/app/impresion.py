import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .models import Comanda, utcnow

logger = logging.getLogger(__name__)

NOMBRE_RESTAURANTE = "VARCINO: PARRILLA Y SOPAS"


def generar_ticket(comanda: Comanda) -> str:
    pedido = comanda.pedido
    recibida = comanda.recibida_en.strftime("%Y-%m-%d %H:%M:%S")
    lineas = [
        "=" * 42,
        NOMBRE_RESTAURANTE.center(42),
        "=" * 42,
        f"Comanda: {comanda.id:06d}".ljust(28) + f"Área: {comanda.area.value}",
        f"Pedido: {pedido.id}".ljust(28) + f"Mesa: {pedido.mesa_numero}",
        f"Mesero: {pedido.mesero.nombre}",
        f"Recibida: {recibida}",
        "-" * 42,
    ]
    for linea in comanda.lineas:
        lineas.append(f"{linea.cantidad} x {linea.nombre}")
        for opcion in linea.opciones:
            lineas.append(f"   Opción: {opcion}")
        if linea.observacion:
            lineas.append(f"   Obs: {linea.observacion}")
    lineas.extend(
        [
            "-" * 42,
            f"Total ítems: {sum(linea.cantidad for linea in comanda.lineas)}",
            "=" * 42,
            "",
        ]
    )
    return "\n".join(lineas)


def _ruta_ticket(comanda: Comanda) -> Path:
    ahora = datetime.now(timezone.utc)
    carpeta = settings.print_dir / comanda.area.value / ahora.strftime("%Y-%m-%d")
    nombre = (
        f"comanda-{comanda.id:06d}-"
        f"{ahora.strftime('%Y%m%d-%H%M%S-%f')}.txt"
    )
    return carpeta / nombre


def imprimir_comanda(comanda: Comanda) -> Path | None:
    ticket = generar_ticket(comanda)
    modo = settings.print_mode

    if modo in {"none", "off", "disabled"}:
        comanda.impresa_en = utcnow()
        return None

    if modo in {"console", "consola"}:
        print(ticket)
        comanda.impresa_en = utcnow()
        return None

    ruta = _ruta_ticket(comanda)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(ticket, encoding="utf-8")
    os.replace(temporal, ruta)

    comanda.impresa_en = utcnow()
    try:
        comanda.archivo_impresion = str(ruta.relative_to(settings.print_dir))
    except ValueError:
        comanda.archivo_impresion = str(ruta)
    logger.info("Comanda %s impresa en %s", comanda.id, ruta)
    return ruta


def ruta_archivo(comanda: Comanda) -> Path | None:
    if not comanda.archivo_impresion:
        return None
    ruta = Path(comanda.archivo_impresion)
    if not ruta.is_absolute():
        ruta = settings.print_dir / ruta
    return ruta
