from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Category, OptionGroup, Product, ProductOptionGroup
from ..schemas import CategoryOut

router = APIRouter(prefix="/api/menu", tags=["menu"])


@router.get("", response_model=list[CategoryOut])
def get_menu(db: Session = Depends(get_db)):
    query = (
        select(Category)
        .options(
            selectinload(Category.products)
            .selectinload(Product.option_links)
            .selectinload(ProductOptionGroup.group)
            .selectinload(OptionGroup.options)
        )
        .order_by(Category.position)
    )
    return db.scalars(query).all()
