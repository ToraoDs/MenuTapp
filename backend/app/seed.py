from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Category, Option, OptionGroup, Product, ProductOptionGroup

GROUPS = {
    "carne_frijolada": ("Carne", 1, [("Carne de res 200 gr", 0), ("Pancita asada", 0)]),
    "proteina_ensalada": ("Proteína", 1, [("Pancita a la parrilla", 0), ("Pechuga", 0)]),
    "sabor_helado": (
        "Sabor",
        1,
        [
            ("Oreo", 0),
            ("Milky Way", 0),
            ("M&M's", 0),
            ("Frutos del bosque", 0),
            ("Vainilla", 0),
            ("Chocolate", 0),
            ("Arequipe", 0),
        ],
    ),
}


CATEGORIES = [
    ("Entradas", "", 30, [
        ("Chorizo", 17500, "3 chorizos santarrosano acompañados de papa salada.", []),
        ("Chicharrones", 33500, "3 chicharrones acompañados de patacón con queso de untar y pico de gallo.", []),
        ("Patacones", 11500, "5 unidades con hogao y guacamole.", []),
        ("Rellena", 26500, "Acompañada de 8 papas criollas.", []),
        ("Longaniza", 31500, "3 longanizas acompañadas de 8 papas criollas.", []),
    ]),
    ("Sopas", "", 45, [
        ("Ajiaco normal (22 onz)", 33500, "Pierna-pernil, arroz, arepa y aguacate.", []),
        ("Ajiaco pequeño (15 onz)", 21000, "Acompañado de arroz.", []),
        ("Mondongo normal (22 onz)", 33500, "Arroz, arepa y aguacate.", []),
        ("Mondongo pequeño (15 onz)", 21000, "Acompañado de arroz.", []),
        ("Mazamorra normal (22 onz)", 33500, "Espinazo, arroz, arepa y aguacate.", []),
        ("Mazamorra pequeña (15 onz)", 21000, "Acompañada de arroz.", []),
    ]),
    ("Cortes finos", "", 10, [
        ("Pechuga", 45000, "Corte mariposa, papa francesa y plátano.", []),
        ("Churrasco", 48000, "Corte mariposa, papa francesa y plátano.", []),
        ("Punta de anca", 48000, "Corte mariposa, papa francesa y plátano.", []),
    ]),
    ("Frijolada", "", 20, [
        ("Frijolada", 45000, "Frijol bola roja, chicharrón, chorizo, arroz y aguacate (15 onz).", ["carne_frijolada"]),
    ]),
    ("Especialidades", "", 0, [
        ("Mixta 3 carnes", 45000, "Res, pancita asada y costillas, acompañado con papa salada, plátano y arepa boyacense.", []),
        ("Mixta 2 carnes", 45000, "Acompañada con papa salada, plátano y arepa boyacense.", []),
        ("Solo costilla", 48000, "", []),
        ("Medio plato mixta 3 carnes", 30000, "Res, pancita asada y costillas, acompañado con papa salada y plátano.", []),
        ("Insaciable", 75000, "Pancita asada, costillas, res, chorizo santarrosano, chicharrón, rellena, arepas x2, papa salada x2, papa criolla x4.", []),
        ("Parrillada", 105000, "Carne de res, pancita asada, costillas, rellena, longaniza, papa criolla, plátano maduro y 3 arepas.", []),
    ]),
    ("Ensaladas", "", 110, [
        ("Ensalada pequeña", 15500, "Aguacate, tomate cherry, mazorca desgranada, lechuga hidropónica y cebollín.", []),
        ("Mega ensalada gourmet", 39000, "Aguacate, tomate cherry, mazorca desgranada, lechuga hidropónica, cebollín, atún y patacón.", ["proteina_ensalada"]),
    ]),
    ("Adiciones", "", 90, [
        ("Papas a la francesa", 9500, "Porción 120 gr.", []),
        ("Arroz", 5200, "1 porción.", []),
        ("Aguacate", 5100, "1/2.", []),
        ("Plátano", 10500, "1 unidad.", []),
        ("Papa criolla", 11900, "10 unidades.", []),
        ("Arepa", 4000, "1 unidad.", []),
        ("Guacamole", 6800, "3.5 onz.", []),
        ("Papa salada", 10500, "5 unidades.", []),
    ]),
    ("Bebidas", "", 200, [
        ("Vaso de limonada", 5500, "12 onz.", []),
        ("Jarra de limonada", 21000, "6 vasos de 12 onz.", []),
        ("Té limón/durazno", 5600, "", []),
        ("Pony Malta mini", 3300, "", []),
        ("Pony Malta 330 ml", 5400, "", []),
        ("Agua botella", 5000, "", []),
        ("Agua H2O", 5600, "", []),
        ("Jugo Hit 200 ml", 3300, "", []),
        ("Jugo Hit 500 ml", 5600, "", []),
        ("Coca-Cola 400 ml", 5600, "", []),
        ("Gaseosa Postobón 400 ml", 5600, "", []),
    ]),
    ("Cervezas", "", 45, [
        ("Club Colombia", 7000, "", []),
        ("Heineken", 8500, "", []),
        ("Coronita", 7000, "", []),
        ("Águila", 6000, "", []),
        ("Águila light", 6800, "", []),
        ("Poker", 6000, "", []),
        ("Cola y pola", 5500, "", []),
        ("Refajo Andina", 5500, "", []),
    ]),
    ("Helados", "", 330, [
        ("Helado Popsy", 7500, "Helado gourmet.", ["sabor_helado"]),
    ]),
]

def seed_if_empty(db: Session) -> None:
    if db.scalar(select(Category.id).limit(1)) is not None:
        return

    groups: dict[str, OptionGroup] = {}
    for key, (title, max_choices, options) in GROUPS.items():
        groups[key] = OptionGroup(
            title=title,
            max_choices=max_choices,
            options=[Option(name=n, price=p, position=i) for i, (n, p) in enumerate(options)],
        )
    db.add_all(groups.values())

    for c_pos, (name, emoji, hue, products) in enumerate(CATEGORIES):
        category = Category(name=name, emoji=emoji, hue=hue, position=c_pos)
        for p_pos, (p_name, price, description, group_keys) in enumerate(products):
            product = Product(name=p_name, price=price, description=description, position=p_pos)
            product.option_links = [
                ProductOptionGroup(group=groups[key], position=i) for i, key in enumerate(group_keys)
            ]
            category.products.append(product)
        db.add(category)

    db.commit()
