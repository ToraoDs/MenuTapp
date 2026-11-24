def test_crud_menu_y_mesas(client, auth):
    categoria = client.post(
        "/api/menu/categorias",
        headers=auth("admin"),
        json={"nombre": "Pruebas", "area": "PARRILLA", "emoji": "T", "hue": 10},
    )
    assert categoria.status_code == 201, categoria.text
    categoria_id = categoria.json()["id"]

    producto = client.post(
        f"/api/menu/categorias/{categoria_id}/productos",
        headers=auth("admin"),
        json={"nombre": "Producto prueba", "precio": 12345},
    )
    assert producto.status_code == 201, producto.text
    producto_id = producto.json()["id"]

    grupo = client.post(
        "/api/menu/grupos",
        headers=auth("admin"),
        json={"titulo": "Grupo prueba", "max_opciones": 2},
    )
    assert grupo.status_code == 201, grupo.text
    grupo_id = grupo.json()["id"]

    opcion = client.post(
        f"/api/menu/grupos/{grupo_id}/opciones",
        headers=auth("admin"),
        json={"nombre": "Opción prueba", "precio": 1000},
    )
    assert opcion.status_code == 201, opcion.text

    grupos = client.get(
        "/api/menu/grupos", params={"incluir_inactivos": True}, headers=auth("admin")
    )
    assert grupos.status_code == 200, grupos.text
    assert any(g["id"] == grupo_id for g in grupos.json())

    asignado = client.put(
        f"/api/menu/productos/{producto_id}/grupos",
        headers=auth("admin"),
        json={"grupo_ids": [grupo_id]},
    )
    assert asignado.status_code == 200, asignado.text
    assert [g["id"] for g in asignado.json()["grupos"]] == [grupo_id]

    assert (
        client.post(
            "/api/menu/categorias",
            headers=auth("mesero1"),
            json={"nombre": "No permitido", "area": "PARRILLA"},
        ).status_code
        == 403
    )

    assert (
        client.delete(
            f"/api/menu/productos/{producto_id}", headers=auth("admin")
        ).status_code
        == 200
    )
    menu = client.get(
        "/api/menu", params={"incluir_inactivos": True}, headers=auth("admin")
    ).json()
    categoria_menu = next(c for c in menu if c["id"] == categoria_id)
    producto_menu = next(p for p in categoria_menu["productos"] if p["id"] == producto_id)
    assert producto_menu["activo"] is False

    generadas = client.post(
        "/api/mesas/generar",
        headers=auth("admin"),
        json={"desde": 47, "hasta": 48},
    )
    assert generadas.status_code == 200, generadas.text
    assert generadas.json()["creadas"] == [47, 48]

    mesa = client.post(
        "/api/mesas", headers=auth("admin"), json={"numero": 49}
    )
    assert mesa.status_code == 201, mesa.text
    mesa_id = mesa.json()["id"]
    assert (
        client.delete(f"/api/mesas/{mesa_id}", headers=auth("admin")).status_code
        == 200
    )
    mesas = client.get(
        "/api/mesas", params={"incluir_inactivas": True}, headers=auth("admin")
    ).json()
    assert next(m for m in mesas if m["id"] == mesa_id)["activa"] is False
    for numero in (47, 48):
        mesa_generada = next(m for m in mesas if m["numero"] == numero)
        assert (
            client.delete(
                f"/api/mesas/{mesa_generada['id']}", headers=auth("admin")
            ).status_code
            == 200
        )

    desactivada = client.delete(
        f"/api/menu/categorias/{categoria_id}",
        params={"cascade": True},
        headers=auth("admin"),
    )
    assert desactivada.status_code == 200, desactivada.text
