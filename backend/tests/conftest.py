import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["FRONTEND_DIR"] = "/nonexistent"
os.environ["PRINT_DIR"] = tempfile.mkdtemp(prefix="pdv-prints-")
os.environ["SECRET_KEY"] = "clave-de-pruebas-suficientemente-larga-1234567890"
os.environ["LOG_TO_FILE"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.main import app

CREDENCIALES = {
    "admin": ("admin", "admin123"),
    "mesero1": ("mesero1", "mesero123"),
    "mesero2": ("mesero2", "mesero123"),
    "cajera": ("cajera", "cajera123"),
    "parrilla": ("parrilla", "area123"),
    "sopas": ("sopas", "area123"),
    "bebidas": ("bebidas", "area123"),
    "patinador": ("patinador", "patinador123"),
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def tokens(client):
    resultado = {}
    for clave, (usuario, contrasena) in CREDENCIALES.items():
        respuesta = client.post(
            "/api/auth/login",
            json={"usuario": usuario, "contrasena": contrasena},
        )
        assert respuesta.status_code == 200, respuesta.text
        resultado[clave] = respuesta.json()["access_token"]
    return resultado


@pytest.fixture(scope="session")
def auth(tokens):
    def _auth(usuario: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {tokens[usuario]}"}

    return _auth


@pytest.fixture(scope="session")
def menu(client, auth):
    respuesta = client.get("/api/menu", headers=auth("mesero1"))
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


@pytest.fixture(scope="session")
def buscar(menu):
    def _buscar(nombre: str) -> dict:
        return next(
            producto
            for categoria in menu
            for producto in categoria["productos"]
            if producto["nombre"] == nombre
        )

    return _buscar
