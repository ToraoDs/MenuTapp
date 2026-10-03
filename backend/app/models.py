from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    emoji: Mapped[str] = mapped_column(String(8), default="")
    hue: Mapped[int] = mapped_column(default=0)
    position: Mapped[int] = mapped_column(default=0)

    products: Mapped[list["Product"]] = relationship(
        back_populates="category", order_by="Product.position"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[int]
    description: Mapped[str] = mapped_column(String(500), default="")
    position: Mapped[int] = mapped_column(default=0)

    category: Mapped[Category] = relationship(back_populates="products")
    option_links: Mapped[list["ProductOptionGroup"]] = relationship(
        order_by="ProductOptionGroup.position", cascade="all, delete-orphan"
    )

    @property
    def option_groups(self) -> list["OptionGroup"]:
        return [link.group for link in self.option_links]


class OptionGroup(Base):
    __tablename__ = "option_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(80))
    max_choices: Mapped[int] = mapped_column(default=1)

    options: Mapped[list["Option"]] = relationship(
        back_populates="group", order_by="Option.position", cascade="all, delete-orphan"
    )


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("option_groups.id"))
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[int] = mapped_column(default=0)
    position: Mapped[int] = mapped_column(default=0)

    group: Mapped[OptionGroup] = relationship(back_populates="options")


class ProductOptionGroup(Base):
    __tablename__ = "product_option_groups"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("option_groups.id"), primary_key=True)
    position: Mapped[int] = mapped_column(default=0)

    group: Mapped[OptionGroup] = relationship()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    paid: Mapped[bool] = mapped_column(default=False)

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order", order_by="OrderLine.id", cascade="all, delete-orphan"
    )

    @property
    def total(self) -> int:
        return sum(line.subtotal for line in self.lines)


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), default=None
    )
    name: Mapped[str] = mapped_column(String(120))
    qty: Mapped[int]
    unit_price: Mapped[int]
    options: Mapped[list[str]] = mapped_column(JSON, default=list)

    order: Mapped[Order] = relationship(back_populates="lines")

    @property
    def subtotal(self) -> int:
        return self.unit_price * self.qty
