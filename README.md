# PDV Restaurante — Varcino: Parrilla y Sopas

Sistema de punto de venta para el restaurante **Varcino: Parrilla y Sopas**. Permite tomar pedidos por mesa, enviarlos como comandas a cada área de preparación, seguir su estado en tiempo real, confirmar la entrega y cobrar en caja con generación de recibo.

Proyecto final de **Programación Avanzada** — Universidad Distrital Francisco José de Caldas.

## Estado actual

- **Backend completo:** autenticación, usuarios, mesas, menú, pedidos, comandas, cuentas, pagos, recibos, reportes y eventos SSE.
- **21 pruebas automatizadas** pasando.
- **Impresión simulada:** cada comanda se escribe como ticket de texto en `backend/impresiones/`.
- **Tiempo real:** los tableros de cocina y caja pueden consumir `GET /api/eventos` mediante Server-Sent Events.
- **Frontend:** existe una maqueta inicial en `frontend/`, pero todavía no está conectada a la API. El backend la sirve en `/`.

## Tecnologías

- Python 3.14
- FastAPI
- SQLAlchemy 2
- SQLite + Alembic
- JWT con PyJWT
- Pytest

## Requisitos

- Python 3.11 o superior
- pip

## Instalación y ejecución

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
./.venv/bin/alembic upgrade head
./.venv/bin/python -m uvicorn app.main:app --reload
```

La aplicación queda disponible en `http://127.0.0.1:8000` y la documentación interactiva en `http://127.0.0.1:8000/docs`.

Al iniciar se crean las tablas si no existen, se aplican los datos iniciales y se completan las mesas hasta `MESAS_TOTAL` (46 por defecto). Para una base nueva también se puede usar `AUTO_CREATE_DB=true` sin ejecutar Alembic.

### Migraciones

```bash
cd backend
./.venv/bin/alembic upgrade head
./.venv/bin/alembic current
./.venv/bin/alembic check
```

Si una base creada por una versión anterior no tiene tabla `alembic_version`, marcar primero la revisión inicial y luego aplicar los cambios:

```bash
./.venv/bin/alembic stamp 95c5af3286e8
./.venv/bin/alembic upgrade head
```

### Variables de entorno

Copiar `backend/.env.example` a `backend/.env` y ajustar los valores. Las variables principales son:

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite:///backend/pdv.db` | Conexión a la base de datos |
| `SECRET_KEY` | Clave de desarrollo | Clave para firmar los tokens JWT |
| `TOKEN_TTL_MINUTES` | `480` | Duración del token de acceso |
| `SSE_TOKEN_TTL_SECONDS` | `60` | Duración del token para SSE |
| `PRINT_MODE` | `file` | `file`, `console` o `none` |
| `PRINT_DIR` | `backend/impresiones` | Carpeta de tickets simulados |
| `APP_TIMEZONE` | `America/Bogota` | Zona horaria de reportes |
| `MESAS_TOTAL` | `46` | Mesas creadas por el seed |
| `SQLITE_WAL` | `true` | Activa WAL para SQLite |
| `SQLITE_BUSY_TIMEOUT_MS` | `5000` | Espera ante bloqueos de SQLite |
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| `LOG_TO_FILE` | `false` | Escribe logs en `LOG_DIR` |
| `CORS_ORIGINS` | `*` | Orígenes permitidos, separados por comas |
| `FRONTEND_DIR` | `frontend/` | Carpeta del frontend estático |

## Usuarios de demostración

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador |
| `mesero1` | `mesero123` | Mesero |
| `mesero2` | `mesero123` | Mesero |
| `cajera` | `cajera123` | Cajera |
| `parrilla` | `area123` | Encargado de parrilla |
| `sopas` | `area123` | Encargado de sopas y entradas |
| `bebidas` | `area123` | Encargado de bebidas |
| `patinador` | `patinador123` | Patinador |

## Flujo de uso

1. El mesero inicia sesión y crea un pedido en borrador para una mesa.
2. Al confirmar el pedido, el sistema genera una comanda por área: parrilla, sopas y entradas, o bebidas. Cada comanda se imprime en un archivo de texto.
3. Cada encargado marca su comanda como `EN_PREPARACION` y luego `LISTO`; el patinador la marca como `ENTREGADO`.
4. El mesero envía la cuenta a caja cuando el pedido está confirmado.
5. La cajera consulta la cuenta, registra el pago, calcula el cambio y obtiene el recibo.
6. Administrador y cajera consultan reportes de ventas por fecha, método de pago, área y producto.

## Roles y áreas

- **Roles:** `MESERO`, `CAJERA`, `ADMINISTRADOR`, `ENCARGADO_AREA`, `PATINADOR`.
- **Áreas:** `PARRILLA`, `SOPAS_ENTRADAS`, `BEBIDAS`.

Asignación de categorías del menú:

| Área | Categorías |
|---|---|
| `SOPAS_ENTRADAS` | Entradas, Sopas, Ensaladas |
| `PARRILLA` | Cortes finos, Frijolada, Especialidades, Adiciones |
| `BEBIDAS` | Bebidas, Cervezas, Helados |

## Autenticación

Todas las rutas de la API, excepto `POST /api/auth/login` y `GET /api/health`, requieren un token JWT en la cabecera:

```
Authorization: Bearer <access_token>
```

### Ejemplo

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "admin", "contrasena": "admin123"}'
```

Para SSE se solicita un token corto con `POST /api/auth/eventos-token` y se usa como query parameter:

```bash
curl -N "http://127.0.0.1:8000/api/eventos?token=<sse_token>"
```

## Endpoints

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| `GET` | `/api/health` | Público | Estado del servicio y la base |
| `POST` | `/api/auth/login` | Público | Iniciar sesión |
| `GET` | `/api/auth/me` | Autenticado | Usuario actual |
| `POST` | `/api/auth/eventos-token` | Autenticado | Token corto para SSE |
| `GET` | `/api/eventos` | Autenticado | Flujo SSE filtrado por rol |
| `GET` | `/api/usuarios` | Administrador | Listar usuarios |
| `POST` | `/api/usuarios` | Administrador | Crear usuario |
| `PUT` | `/api/usuarios/{id}` | Administrador | Actualizar o desactivar usuario |
| `GET` | `/api/menu` | Autenticado | Menú activo o filtrado por `area` |
| `POST` | `/api/menu/categorias` | Administrador | Crear categoría |
| `PUT` | `/api/menu/categorias/{id}` | Administrador | Actualizar categoría |
| `DELETE` | `/api/menu/categorias/{id}` | Administrador | Desactivar categoría (`cascade=true`) |
| `POST` | `/api/menu/categorias/{id}/productos` | Administrador | Crear producto |
| `PUT` | `/api/menu/productos/{id}` | Administrador | Actualizar producto |
| `DELETE` | `/api/menu/productos/{id}` | Administrador | Desactivar producto |
| `PUT` | `/api/menu/productos/{id}/grupos` | Administrador | Asignar grupos de opciones |
| `GET` | `/api/menu/grupos` | Autenticado | Listar grupos de opciones |
| `GET` | `/api/menu/grupos/{id}` | Autenticado | Consultar grupo de opciones |
| `POST` | `/api/menu/grupos` | Administrador | Crear grupo de opciones |
| `PUT` | `/api/menu/grupos/{id}` | Administrador | Actualizar grupo |
| `DELETE` | `/api/menu/grupos/{id}` | Administrador | Desactivar grupo |
| `POST` | `/api/menu/grupos/{id}/opciones` | Administrador | Crear opción |
| `PUT` | `/api/menu/opciones/{id}` | Administrador | Actualizar opción |
| `DELETE` | `/api/menu/opciones/{id}` | Administrador | Desactivar opción |
| `GET` | `/api/mesas` | Autenticado | Listar mesas y su estado |
| `POST` | `/api/mesas` | Administrador | Crear mesa |
| `POST` | `/api/mesas/generar` | Administrador | Generar mesas en un rango |
| `PUT` | `/api/mesas/{id}` | Administrador | Actualizar mesa |
| `DELETE` | `/api/mesas/{id}` | Administrador | Desactivar mesa |
| `POST` | `/api/pedidos` | Mesero, Administrador | Crear pedido en borrador |
| `GET` | `/api/pedidos` | Mesero, Administrador | Listar pedidos propios o todos |
| `GET` | `/api/pedidos/mesa/{numero}` | Mesero, Administrador | Pedidos de una mesa |
| `GET` | `/api/pedidos/{id}` | Mesero, Administrador | Consultar pedido |
| `PUT` | `/api/pedidos/{id}` | Mesero, Administrador | Modificar pedido |
| `DELETE` | `/api/pedidos/{id}` | Mesero, Administrador | Cancelar pedido lógicamente |
| `POST` | `/api/pedidos/{id}/confirmar` | Mesero, Administrador | Confirmar y generar comandas |
| `GET` | `/api/comandas` | Encargado de área, Patinador, Administrador | Listar comandas |
| `PUT` | `/api/comandas/{id}/estado` | Encargado de área, Administrador | Cambiar estado |
| `POST` | `/api/comandas/{id}/entregar` | Patinador, Mesero, Administrador | Confirmar entrega |
| `POST` | `/api/comandas/{id}/imprimir` | Encargado de área, Administrador | Reimprimir comanda |
| `GET` | `/api/comandas/{id}/ticket` | Encargado de área, Administrador | Descargar ticket de texto |
| `GET` | `/api/cuentas` | Cajera, Administrador | Listar cuentas confirmadas |
| `GET` | `/api/cuentas/mesa/{numero}` | Cajera, Administrador | Cuenta abierta de una mesa |
| `GET` | `/api/cuentas/{id}` | Cajera, Administrador | Consultar cuenta |
| `POST` | `/api/cuentas/{id}/enviar-caja` | Mesero, Administrador | Enviar cuenta a caja |
| `POST` | `/api/cuentas/{id}/pagar` | Cajera, Administrador | Registrar pago y cerrar cuenta |
| `GET` | `/api/cuentas/{id}/recibo` | Cajera, Administrador | Consultar recibo |
| `GET` | `/api/reportes/ventas` | Cajera, Administrador | Reporte de ventas por rango |
| `GET` | `/api/reportes/productos` | Cajera, Administrador | Productos más vendidos |

## Reglas de negocio

- Todo pedido requiere una mesa y un mesero.
- Solo puede existir una cuenta abierta por mesa.
- Los precios y las opciones se calculan y validan en el servidor.
- Un producto libre requiere nombre, precio y área.
- Las comandas siguen el orden `PENDIENTE → EN_PREPARACION → LISTO → ENTREGADO`, guardando la hora de cada cambio.
- Un pedido se puede modificar o cancelar mientras todas sus comandas estén `PENDIENTE`. Si ya está en preparación, solo el administrador puede hacerlo.
- La cancelación es lógica: el pedido conserva su historial, se marca `CANCELADO` y deja de sumar en la cuenta.
- Cada cuenta admite un único pago y el valor recibido debe cubrir el total; el cambio se guarda y se muestra en el recibo.
- Los productos, categorías, grupos y opciones se desactivan lógicamente para no romper pedidos históricos.
- El reporte de ventas usa cuentas pagadas y fechas en la zona horaria configurada.

## Pruebas

```bash
cd backend
./.venv/bin/python -m pytest -q
```

Resultado esperado:

```
21 passed
```

Las pruebas cubren autenticación y permisos, menú y áreas, CRUD administrativo, validación de pedidos y opciones, generación y transiciones de comandas, impresión/reimpresión, entrega, cuentas, pagos, recibos, reportes y token SSE.

## Estructura del proyecto

```
backend/
  app/
    main.py              # Aplicación FastAPI, CORS, errores y arranque
    config.py            # Variables de entorno
    database.py          # Conexión, WAL y sesión de SQLAlchemy
    logging_config.py    # Configuración de logs
    models.py            # Modelos y enums en español
    schemas.py           # Esquemas Pydantic
    security.py          # Hash, JWT, tokens SSE y permisos
    events.py            # Bus SSE en memoria
    impresion.py         # Tickets simulados en archivos
    services.py          # Reglas de negocio
    seed.py              # Datos iniciales
    routers/
      auth.py            # Login, usuario actual y token SSE
      usuarios.py        # Administración de usuarios
      menu.py            # Menú, mesas y CRUD administrativo
      pedidos.py         # Pedidos y comandas
      cuentas.py         # Caja, pagos y recibos
      reportes.py        # Reportes de ventas y productos
      eventos.py         # Endpoint SSE
  alembic/               # Migraciones
  tests/
  pdv.db                 # Base de datos SQLite (generada)
  impresiones/           # Tickets simulados (generada)
  logs/                  # Logs (generada)
frontend/                # Maqueta inicial, aún no conectada
documentos/              # Documento del proyecto y diagramas
```

## Documentación

El documento del proyecto y los diagramas UML se encuentran en `documentos/`.
