from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Category, Option, OptionGroup, Product, ProductOptionGroup

GROUPS = {
    "bebidas": (
        "Bebida",
        1,
        [
            ("Coca Cola 400ml", 4000),
            ("Coca Cola sin azúcar 400ml", 4000),
            ("Ginger 400ml", 4000),
            ("Agua Brisa 600ml", 4000),
            ("Hit de mango 400ml", 4000),
            ("Hit de mora 400ml", 4000),
            ("Coronita 210ml", 5000),
            ("Tres Cordilleras", 8000),
            ("Coca Cola 1.5 Lt", 8000),
            ("Sprite 1.5 Lt", 8000),
        ],
    ),
    "teriyaki": (
        "Teriyaki",
        3,
        [("Salsa teriyaki extra", 1000), ("Mayonesa de sushi", 1000), ("Jengibre", 0), ("Wasabi", 0)],
    ),
    "salsas": (
        "Salsas",
        2,
        [("BBQ", 1000), ("Ajo", 1000), ("Piña", 1000), ("Picante", 0)],
    ),
}

CATEGORIES = [
    ("Hamburguesas", "", 20, [
        ("Hamburguesa clásica", 16900, "Carne, queso, lechuga y tomate.", ["salsas", "bebidas"]),
        ("Hamburguesa doble", 22900, "Doble carne y queso cheddar.", ["salsas", "bebidas"]),
    ]),
    ("Pizza 27cm (6 porciones)", "", 30, [
        ("Pizza pepperoni", 24900, "Queso mozzarella y pepperoni.", ["bebidas"]),
        ("Pizza hawaiana", 24900, "Jamón y piña.", ["bebidas"]),
    ]),
    ("Alitas", "", 10, [
        ("Alitas x8", 21900, "Ocho alitas con salsa a elección.", ["salsas", "bebidas"]),
    ]),
    ("Costillas BBQ", "", 0, [
        ("Costillas BBQ", 32900, "Media tira con salsa BBQ.", ["bebidas"]),
    ]),
    ("Salchipapa", "", 40, [
        ("Salchipapa clásica", 14900, "Papa, salchicha y salsas.", ["salsas", "bebidas"]),
    ]),
    ("Perro caliente", "", 35, [
        ("Perro americano", 12900, "Salchicha, queso y papa ripio.", ["salsas", "bebidas"]),
    ]),
    ("Lasaña", "", 25, [
        ("Lasagna de carne", 18900, "Lasaña gratinada con carne y pan.", ["bebidas"]),
    ]),
    ("Sushi makis especiales", "", 200, [
        ("Crispy Philadelphia", 27900,
         "Diez makis rellenos de salmón, queso crema, aguacate y mayonesa picante, envueltos en tempura y panko, servidos con salsa teriyaki y mayonesa de sushi.",
         ["bebidas", "teriyaki"]),
    ]),
    ("Sushi nori makis", "", 210, [
        ("California roll", 22900, "Diez makis de kanikama y aguacate.", ["bebidas", "teriyaki"]),
    ]),
    ("Sushi combos", "", 190, [
        ("Combo x30", 69900, "Treinta piezas surtidas.", ["bebidas", "teriyaki"]),
    ]),
    ("Cervezas", "", 45, [
        ("Cerveza Club Colombia", 6000, "Botella 330ml.", []),
        ("Cerveza Corona", 9000, "Botella 355ml.", []),
    ]),
    ("Jugos Hit", "", 130, [
        ("Jugo Hit de mango", 4000, "Caja 400ml.", []),
        ("Jugo Hit de mora", 4000, "Caja 400ml.", []),
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
