def test_login_correcto(client):
    respuesta = client.post(
        "/api/auth/login", json={"usuario": "admin", "contrasena": "admin123"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["usuario"]["rol"] == "ADMINISTRADOR"
    assert "contrasena_hash" not in cuerpo["usuario"]


def test_login_incorrecto(client):
    respuesta = client.post(
        "/api/auth/login", json={"usuario": "admin", "contrasena": "mala"}
    )
    assert respuesta.status_code == 401


def test_endpoint_sin_token(client):
    assert client.get("/api/menu").status_code == 401


def test_rol_denegado(client, auth):
    assert client.get("/api/usuarios", headers=auth("mesero1")).status_code == 403


def test_me(client, auth):
    respuesta = client.get("/api/auth/me", headers=auth("mesero1"))
    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"] == "mesero1"


def test_admin_crea_y_desactiva_usuario(client, auth):
    respuesta = client.post(
        "/api/usuarios",
        headers=auth("admin"),
        json={
            "nombre": "Temporal",
            "usuario": "temporal",
            "contrasena": "temporal123",
            "rol": "MESERO",
        },
    )
    assert respuesta.status_code == 201
    usuario_id = respuesta.json()["id"]

    assert (
        client.post(
            "/api/auth/login",
            json={"usuario": "temporal", "contrasena": "temporal123"},
        ).status_code
        == 200
    )

    respuesta = client.put(
        f"/api/usuarios/{usuario_id}",
        headers=auth("admin"),
        json={"activo": False},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False

    assert (
        client.post(
            "/api/auth/login",
            json={"usuario": "temporal", "contrasena": "temporal123"},
        ).status_code
        == 401
    )
