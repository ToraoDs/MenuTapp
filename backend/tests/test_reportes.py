from datetime import datetime
from zoneinfo import ZoneInfo


def test_flujo_caja_reimpresion_y_reportes(client, auth, buscar):
    producto = buscar("Chorizo")
    creado = client.post(
        "/api/pedidos",
        headers=auth("mesero1"),
        json={
            "mesa_numero": 40,
            "lineas": [{"producto_id": producto["id"], "cantidad": 2}],
        },
    )
    assert creado.status_code == 201, creado.text
    pedido = creado.json()

    confirmado = client.post(
        f"/api/pedidos/{pedido['id']}/confirmar", headers=auth("mesero1")
    )
    assert confirmado.status_code == 200, confirmado.text
    comanda = confirmado.json()["comandas"][0]

    impresa = client.post(
        f"/api/comandas/{comanda['id']}/imprimir", headers=auth("admin")
    )
    assert impresa.status_code == 200, impresa.text
    assert impresa.json()["archivo_impresion"]

    ticket = client.get(
        f"/api/comandas/{comanda['id']}/ticket", headers=auth("admin")
    )
    assert ticket.status_code == 200
    assert "VARCINO" in ticket.text

    abierta = client.get("/api/cuentas/mesa/40", headers=auth("cajera"))
    assert abierta.status_code == 200
    assert abierta.json()["id"] == pedido["cuenta_id"]

    enviada = client.post(
        f"/api/cuentas/{pedido['cuenta_id']}/enviar-caja", headers=auth("mesero1")
    )
    assert enviada.status_code == 200, enviada.text
    assert enviada.json()["enviada_caja_en"] is not None

    total = 2 * producto["precio"]
    pagado = total + 10000
    pago = client.post(
        f"/api/cuentas/{pedido['cuenta_id']}/pagar",
        headers=auth("cajera"),
        json={"metodo": "EFECTIVO", "valor": pagado},
    )
    assert pago.status_code == 201, pago.text
    assert pago.json()["total"] == total
    assert pago.json()["cambio"] == 10000

    hoy = datetime.now(ZoneInfo("America/Bogota")).date().isoformat()
    reporte = client.get(
        "/api/reportes/ventas",
        params={"desde": hoy, "hasta": hoy},
        headers=auth("admin"),
    )
    assert reporte.status_code == 200, reporte.text
    datos = reporte.json()
    assert datos["total_ventas"] >= total
    assert datos["cuentas_pagadas"] >= 1
    assert any(m["metodo"] == "EFECTIVO" and m["total"] >= total for m in datos["por_metodo"])

    productos = client.get(
        "/api/reportes/productos",
        params={"desde": hoy, "hasta": hoy, "limite": 100},
        headers=auth("admin"),
    )
    assert productos.status_code == 200
    assert any(
        p["producto_id"] == producto["id"] and p["cantidad"] >= 2
        for p in productos.json()["productos"]
    )

    assert (
        client.get("/api/reportes/ventas", headers=auth("mesero1")).status_code
        == 403
    )


def test_token_sse(client, auth):
    respuesta = client.post("/api/auth/eventos-token", headers=auth("mesero1"))
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["token"]
    assert datos["token_type"] == "sse"
    assert datos["expira_en_segundos"] > 0
