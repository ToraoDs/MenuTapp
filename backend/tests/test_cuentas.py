def test_total_pago_y_recibo(client, auth, buscar):
    creado = client.post(
        "/api/pedidos",
        headers=auth("mesero1"),
        json={
            "mesa_numero": 5,
            "lineas": [
                {"producto_id": buscar("Frijolada")["id"]},
                {"producto_id": buscar("Club Colombia")["id"], "cantidad": 2},
            ],
        },
    ).json()
    cuenta_id = creado["cuenta_id"]
    client.post(f"/api/pedidos/{creado['id']}/confirmar", headers=auth("mesero1"))

    abiertas = client.get(
        "/api/cuentas", params={"estado": "ABIERTA"}, headers=auth("cajera")
    ).json()
    cuenta = next(c for c in abiertas if c["id"] == cuenta_id)
    assert cuenta["mesa_numero"] == 5
    assert cuenta["total"] == 45000 + 2 * 7000
    assert cuenta["estado"] == "ABIERTA"

    insuficiente = client.post(
        f"/api/cuentas/{cuenta_id}/pagar",
        headers=auth("cajera"),
        json={"metodo": "EFECTIVO", "valor": 1000},
    )
    assert insuficiente.status_code == 422

    pago = client.post(
        f"/api/cuentas/{cuenta_id}/pagar",
        headers=auth("cajera"),
        json={"metodo": "EFECTIVO", "valor": 59000},
    )
    assert pago.status_code == 201, pago.text
    recibo = pago.json()
    assert recibo["numero_recibo"] == f"REC-{cuenta_id:06d}"
    assert recibo["total"] == 59000
    assert recibo["metodo"] == "EFECTIVO"
    assert recibo["valor"] == 59000
    assert len(recibo["lineas"]) == 2

    consulta = client.get(
        f"/api/cuentas/{cuenta_id}/recibo", headers=auth("cajera")
    )
    assert consulta.status_code == 200
    assert consulta.json()["numero_recibo"] == recibo["numero_recibo"]

    doble = client.post(
        f"/api/cuentas/{cuenta_id}/pagar",
        headers=auth("cajera"),
        json={"metodo": "TARJETA", "valor": 59000},
    )
    assert doble.status_code == 422

    pagadas = client.get(
        "/api/cuentas", params={"estado": "PAGADA"}, headers=auth("cajera")
    ).json()
    assert any(c["id"] == cuenta_id for c in pagadas)

    nuevo = client.post(
        "/api/pedidos",
        headers=auth("mesero1"),
        json={
            "mesa_numero": 5,
            "lineas": [{"producto_id": buscar("Chorizo")["id"]}],
        },
    ).json()
    assert nuevo["cuenta_id"] != cuenta_id

    abiertas = client.get(
        "/api/cuentas", params={"estado": "ABIERTA"}, headers=auth("cajera")
    ).json()
    assert all(c["mesa_numero"] != 5 for c in abiertas)
    abiertas = client.get(
        "/api/cuentas",
        params={"estado": "ABIERTA", "incluir_borradores": True},
        headers=auth("cajera"),
    ).json()
    assert any(c["mesa_numero"] == 5 for c in abiertas)


def test_cajera_no_accede_a_pedidos(client, auth):
    assert client.get("/api/pedidos", headers=auth("cajera")).status_code == 403
