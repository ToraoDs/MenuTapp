def opcion(producto, grupo_titulo, nombre):
    grupo = next(g for g in producto["grupos"] if g["titulo"] == grupo_titulo)
    return next(o for o in grupo["opciones"] if o["nombre"] == nombre)


def crear_pedido(client, auth, usuario, mesa, lineas):
    return client.post(
        "/api/pedidos",
        headers=auth(usuario),
        json={"mesa_numero": mesa, "lineas": lineas},
    )


def test_borrador_y_confirmacion_por_area(client, auth, buscar):
    frijolada = buscar("Frijolada")
    club = buscar("Club Colombia")
    helado = buscar("Helado Popsy")

    respuesta = crear_pedido(
        client,
        auth,
        "mesero1",
        1,
        [
            {
                "producto_id": frijolada["id"],
                "cantidad": 1,
                "opcion_ids": [opcion(frijolada, "Carne", "Carne de res 200 gr")["id"]],
            },
            {"producto_id": club["id"], "cantidad": 2},
            {
                "producto_id": helado["id"],
                "opcion_ids": [opcion(helado, "Sabor", "Oreo")["id"]],
            },
        ],
    )
    assert respuesta.status_code == 201, respuesta.text
    pedido = respuesta.json()
    assert pedido["confirmado"] is False
    assert pedido["comandas"] == []
    assert pedido["mesero"]["usuario"] == "mesero1"
    assert [linea["area"] for linea in pedido["lineas"]] == [
        "PARRILLA",
        "BEBIDAS",
        "BEBIDAS",
    ]
    assert pedido["total"] == 45000 + 2 * 7000 + 7500

    visibles = client.get(
        "/api/cuentas", params={"estado": "ABIERTA"}, headers=auth("cajera")
    ).json()
    assert all(c["mesa_numero"] != 1 for c in visibles)

    cuentas = client.get(
        "/api/cuentas",
        params={"estado": "ABIERTA", "incluir_borradores": True},
        headers=auth("cajera"),
    ).json()
    cuenta = next(c for c in cuentas if c["mesa_numero"] == 1)
    assert cuenta["total"] == pedido["total"]

    respuesta = client.post(
        f"/api/pedidos/{pedido['id']}/confirmar", headers=auth("mesero1")
    )
    assert respuesta.status_code == 200, respuesta.text
    confirmado = respuesta.json()
    assert confirmado["confirmado"] is True
    assert len(confirmado["comandas"]) == 2
    areas = {comanda["area"]: len(comanda["lineas"]) for comanda in confirmado["comandas"]}
    assert areas == {"PARRILLA": 1, "BEBIDAS": 2}

    repetido = client.post(
        f"/api/pedidos/{pedido['id']}/confirmar", headers=auth("mesero1")
    )
    assert repetido.status_code == 422


def test_validaciones_y_producto_libre(client, auth, buscar):
    frijolada = buscar("Frijolada")
    ensalada = buscar("Mega ensalada gourmet")
    club = buscar("Club Colombia")

    respuesta = crear_pedido(
        client,
        auth,
        "mesero1",
        6,
        [{"producto_id": ensalada["id"], "opcion_ids": [
            opcion(ensalada, "Proteína", "Pechuga")["id"]
        ]}],
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["lineas"][0]["precio_unitario"] == 39000

    ajeno = crear_pedido(
        client,
        auth,
        "mesero1",
        6,
        [{"producto_id": club["id"], "opcion_ids": [
            opcion(ensalada, "Proteína", "Pechuga")["id"]
        ]}],
    )
    assert ajeno.status_code == 422

    demasiadas = crear_pedido(
        client,
        auth,
        "mesero1",
        6,
        [{"producto_id": frijolada["id"], "opcion_ids": [
            o["id"] for o in frijolada["grupos"][0]["opciones"]
        ]}],
    )
    assert demasiadas.status_code == 422

    libre_sin_area = crear_pedido(
        client,
        auth,
        "mesero1",
        6,
        [{"nombre": "Adicional", "precio_unitario": 5000}],
    )
    assert libre_sin_area.status_code == 422

    libre = crear_pedido(
        client,
        auth,
        "mesero1",
        6,
        [
            {
                "nombre": "Adicional",
                "precio_unitario": 5000,
                "area": "PARRILLA",
                "observacion": "Sin sal",
            }
        ],
    )
    assert libre.status_code == 201
    assert libre.json()["lineas"][0]["observacion"] == "Sin sal"

    assert crear_pedido(
        client, auth, "mesero1", 6, [{"producto_id": 9999}]
    ).status_code == 422


def test_requiere_mesa_y_aislamiento_entre_meseros(client, auth, buscar):
    assert crear_pedido(client, auth, "mesero1", 99, [
        {"producto_id": buscar("Chorizo")["id"]}
    ]).status_code == 422

    assert client.post(
        "/api/pedidos", headers=auth("mesero1"), json={"mesa_numero": 7, "lineas": []}
    ).status_code == 422

    creado = crear_pedido(
        client, auth, "mesero1", 7, [{"producto_id": buscar("Chorizo")["id"]}]
    ).json()

    assert (
        client.get(f"/api/pedidos/{creado['id']}", headers=auth("mesero2")).status_code
        == 403
    )
    propios = client.get("/api/pedidos", headers=auth("mesero2")).json()
    assert all(pedido["mesero"]["usuario"] == "mesero2" for pedido in propios)


def test_modificar_y_cancelar_con_autorizacion(client, auth, buscar):
    creado = crear_pedido(
        client, auth, "mesero1", 2, [{"producto_id": buscar("Frijolada")["id"]}]
    ).json()
    pedido_id = creado["id"]

    confirmado = client.post(
        f"/api/pedidos/{pedido_id}/confirmar", headers=auth("mesero1")
    ).json()
    comanda_id = confirmado["comandas"][0]["id"]

    modificado = client.put(
        f"/api/pedidos/{pedido_id}",
        headers=auth("mesero1"),
        json={
            "mesa_numero": 2,
            "lineas": [{"producto_id": buscar("Pechuga")["id"], "cantidad": 2}],
        },
    )
    assert modificado.status_code == 200, modificado.text
    assert modificado.json()["total"] == 90000
    assert len(modificado.json()["comandas"]) == 1

    comanda_id = modificado.json()["comandas"][0]["id"]
    estado = client.put(
        f"/api/comandas/{comanda_id}/estado",
        headers=auth("parrilla"),
        json={"estado": "EN_PREPARACION"},
    )
    assert estado.status_code == 200

    bloqueado = client.put(
        f"/api/pedidos/{pedido_id}",
        headers=auth("mesero1"),
        json={"mesa_numero": 2, "lineas": [{"producto_id": buscar("Pechuga")["id"]}]},
    )
    assert bloqueado.status_code == 403

    permitido = client.put(
        f"/api/pedidos/{pedido_id}",
        headers=auth("admin"),
        json={"mesa_numero": 2, "lineas": [{"producto_id": buscar("Pechuga")["id"]}]},
    )
    assert permitido.status_code == 200, permitido.text

    comanda_id = permitido.json()["comandas"][0]["id"]
    assert client.put(
        f"/api/comandas/{comanda_id}/estado",
        headers=auth("parrilla"),
        json={"estado": "EN_PREPARACION"},
    ).status_code == 200

    assert (
        client.delete(f"/api/pedidos/{pedido_id}", headers=auth("mesero1")).status_code
        == 403
    )
    assert (
        client.delete(f"/api/pedidos/{pedido_id}", headers=auth("admin")).status_code
        == 204
    )
    cancelado = client.get(f"/api/pedidos/{pedido_id}", headers=auth("admin"))
    assert cancelado.status_code == 200
    assert cancelado.json()["estado"] == "CANCELADO"
    assert cancelado.json()["cancelado_en"] is not None
