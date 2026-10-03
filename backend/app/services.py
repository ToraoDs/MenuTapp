from collections import Counter

from sqlalchemy.orm import Session

from .models import Option, OrderLine, Product
from .schemas import LineIn


class DomainError(Exception):
    pass


def build_line(db: Session, data: LineIn) -> OrderLine:
    if data.product_id is None:
        return OrderLine(
            product_id=None,
            name=data.name.strip(),
            qty=data.qty,
            unit_price=data.unit_price,
            options=[],
        )

    product = db.get(Product, data.product_id)
    if product is None:
        raise DomainError(f"El producto {data.product_id} no existe")

    groups = {group.id: group for group in product.option_groups}
    available: dict[int, Option] = {
        option.id: option for group in groups.values() for option in group.options
    }

    if len(set(data.option_ids)) != len(data.option_ids):
        raise DomainError("No se puede repetir una opción")

    chosen: list[Option] = []
    for option_id in data.option_ids:
        option = available.get(option_id)
        if option is None:
            raise DomainError(f"La opción {option_id} no corresponde a «{product.name}»")
        chosen.append(option)

    per_group = Counter(option.group_id for option in chosen)
    for group_id, count in per_group.items():
        group = groups[group_id]
        if count > group.max_choices:
            raise DomainError(f"«{group.title}» permite máximo {group.max_choices} opción(es)")

    return OrderLine(
        product_id=product.id,
        name=product.name,
        qty=data.qty,
        unit_price=product.price + sum(option.price for option in chosen),
        options=[option.name for option in chosen],
    )
