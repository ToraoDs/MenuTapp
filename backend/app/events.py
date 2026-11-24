import asyncio
import itertools
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class EventoBus:
    def __init__(self, max_cola: int = 200) -> None:
        self._max_cola = max_cola
        self._loop: asyncio.AbstractEventLoop | None = None
        self._suscriptores: set[asyncio.Queue] = set()
        self._lock = threading.Lock()
        self._secuencia = itertools.count(1)

    def vincular_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def suscribir(self) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue(maxsize=self._max_cola)
        with self._lock:
            self._suscriptores.add(cola)
        logger.info("SSE suscriptor conectado; total=%s", len(self._suscriptores))
        return cola

    def desuscribir(self, cola: asyncio.Queue) -> None:
        with self._lock:
            self._suscriptores.discard(cola)
        logger.info("SSE suscriptor desconectado; total=%s", len(self._suscriptores))

    def publicar(self, evento: dict[str, Any]) -> None:
        payload = {"id": next(self._secuencia), **evento}
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._entregar, payload)
        else:
            logger.debug("Evento sin loop activo: %s", payload)

    def _entregar(self, payload: dict[str, Any]) -> None:
        with self._lock:
            suscriptores = list(self._suscriptores)
        for cola in suscriptores:
            try:
                cola.put_nowait(payload)
            except asyncio.QueueFull:
                with self._lock:
                    self._suscriptores.discard(cola)
                logger.warning("SSE suscriptor lento desconectado")


evento_bus = EventoBus()
