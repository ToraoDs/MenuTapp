def test_flujo_de_comandas_por_area(client, auth, buscar):
    respuesta = client.post(
        "/api/pedidos",
        headers=auth("mesero1"),
        json={
            "mesa_numero": 4,
            "lineas": [
                {"producto_id": buscar("Frijolada")["id"]},
                {"producto_id": buscar("Chorizo")["id"]},
                {"producto_id": buscar("Club Colombia")["id"]},
            ],
        },
    )
    pedido_id = respuesta.json()["id"]
    confirmado = client.post(
        f"/api/pedidos/{pedido_id}/confirmar", headers=auth("mesero1")
    ).json()
    assert len(confirmado["comandas"]) == 3

    todas = client.get("/api/comandas", headers=auth("admin")).json()
    del_pedido = [c for c in todas if c["pedido_id"] == pedido_id]
    por_area = {c["area"]: c for c in del_pedido}
    assert set(por_area) == {"PARRILLA", "SOPAS_ENTRADAS", "BEBIDAS"}

    parrilla = client.get("/api/comandas", headers=auth("parrilla")).json()
    assert all(c["area"] == "PARRILLA" for c in parrilla)
    assert any(c["id"] == por_area["PARRILLA"]["id"] for c in parrilla)

    sopas = client.get("/api/comandas", headers=auth("sopas")).json()
    assert all(c["area"] == "SOPAS_ENTRADAS" for c in sopas)

    ajeno = client.put(
        f"/api/comandas/{por_area['BEBIDAS']['id']}/estado",
        headers=auth("parrilla"),
        json={"estado": "EN_PREPARACION"},
    )
    assert ajeno.status_code == 403

    comanda_id = por_area["PARRILLA"]["id"]
    en_preparacion = client.put(
        f"/api/comandas/{comanda_id}/estado",
        headers=auth("parrilla"),
        json={"estado": "EN_PREPARACION"},
    )
    assert en_preparacion.status_code == 200
    assert en_preparacion.json()["estado"] == "EN_PREPARACION"

    listo = client.put(
        f"/api/comandas/{comanda_id}/estado",
        headers=auth("parrilla"),
        json={"estado": "LISTO"},
    )
    assert listo.status_code == 200
    assert listo.json()["lista_en"] is not None

    retroceso = client.put(
        f"/api/comandas/{comanda_id}/estado",
        headers=auth("parrilla"),
        json={"estado": "EN_PREPARACION"},
    )
    assert retroceso.status_code == 422

    listas = client.get("/api/comandas", headers=auth("patinador")).json()
    assert all(c["estado"] == "LISTO" for c in listas)
    assert any(c["id"] == comanda_id for c in listas)

    entrega = client.post(
        f"/api/comandas/{comanda_id}/entregar", headers=auth("patinador")
    )
    assert entrega.status_code == 200
    assert entrega.json()["estado"] == "ENTREGADO"
    assert entrega.json()["entregada_en"] is not None

    listas = client.get("/api/comandas", headers=auth("patinador")).json()
    assert not any(c["id"] == comanda_id for c in listas)

    repetida = client.post(
        f"/api/comandas/{comanda_id}/entregar", headers=auth("patinador")
    )
    assert repetida.status_code == 422
