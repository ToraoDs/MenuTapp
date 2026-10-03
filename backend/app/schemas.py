from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OptionOut(ORMModel):
    id: int
    name: str
    price: int


class OptionGroupOut(ORMModel):
    id: int
    title: str
    max_choices: int
    options: list[OptionOut]


class ProductOut(ORMModel):
    id: int
    name: str
    price: int
    description: str
    option_groups: list[OptionGroupOut]


class CategoryOut(ORMModel):
    id: int
    name: str
    emoji: str
    hue: int
    products: list[ProductOut]


class LineIn(BaseModel):
    product_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    unit_price: int | None = Field(default=None, gt=0)
    qty: int = Field(default=1, ge=1, le=99)
    option_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def free_product_needs_name_and_price(self):
        if self.product_id is None and (not self.name or self.unit_price is None):
            raise ValueError("Un producto libre requiere name y unit_price")
        return self


class OrderIn(BaseModel):
    paid: bool = False
    lines: list[LineIn] = Field(min_length=1)


class LineOut(ORMModel):
    id: int
    product_id: int | None
    name: str
    qty: int
    unit_price: int
    options: list[str]
    subtotal: int


class OrderOut(ORMModel):
    id: int
    created_at: datetime
    paid: bool
    lines: list[LineOut]
    total: int

    @field_validator("created_at")
    @classmethod
    def mark_as_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
