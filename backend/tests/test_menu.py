def test_menu_seed_completo(menu):
    assert len(menu) == 10
    assert menu[0]["nombre"] == "Entradas"
    assert all("area" in categoria for categoria in menu)


def test_areas_asignadas(menu):
    areas = {categoria["nombre"]: categoria["area"] for categoria in menu}
    assert areas["Sopas"] == "SOPAS_ENTRADAS"
    assert areas["Cortes finos"] == "PARRILLA"
    assert areas["Adiciones"] == "PARRILLA"
    assert areas["Bebidas"] == "BEBIDAS"
    assert areas["Helados"] == "BEBIDAS"


def test_grupos_de_opciones(buscar):
    frijolada = buscar("Frijolada")
    assert [grupo["titulo"] for grupo in frijolada["grupos"]] == ["Carne"]
    assert frijolada["grupos"][0]["max_opciones"] == 1
    assert buscar("Club Colombia")["grupos"] == []


def test_filtro_por_area(client, auth):
    respuesta = client.get(
        "/api/menu", params={"area": "BEBIDAS"}, headers=auth("mesero1")
    )
    assert respuesta.status_code == 200
    assert {categoria["area"] for categoria in respuesta.json()} == {"BEBIDAS"}


def test_mesas_disponibles(client, auth):
    respuesta = client.get("/api/mesas", headers=auth("mesero1"))
    assert respuesta.status_code == 200
    mesas = respuesta.json()
    assert len(mesas) == 46
    assert mesas[0]["numero"] == 1
    assert all("cuenta_abierta" in mesa for mesa in mesas)
