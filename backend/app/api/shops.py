from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from backend.app.core.database import get_db
from backend.app.models.models import Shop, MenuCategory, MenuItem
from backend.app.schemas.schemas import ShopOut, ShopDetailOut, MenuCategoryOut, MenuItemOut

router = APIRouter(prefix="/shops", tags=["Shops & Menus"])

@router.get("", response_model=List[ShopOut])
async def list_shops(db: AsyncSession = Depends(get_db)):
    """List all available shops at JMD Megapolis"""
    stmt = select(Shop).order_by(Shop.id)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{shop_id_or_slug}", response_model=ShopDetailOut)
async def get_shop_details(shop_id_or_slug: str, db: AsyncSession = Depends(get_db)):
    """Get full shop details including categories and menu items"""
    stmt = (
        select(Shop)
        .options(
            selectinload(Shop.categories).selectinload(MenuCategory.items),
            selectinload(Shop.items),
            selectinload(Shop.prepaid_account)
        )
    )
    if shop_id_or_slug.isdigit():
        stmt = stmt.where(Shop.id == int(shop_id_or_slug))
    else:
        stmt = stmt.where(Shop.slug == shop_id_or_slug)

    res = await db.execute(stmt)
    shop = res.scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    prepaid_bal = None
    if shop.prepaid_account:
        prepaid_bal = float(shop.prepaid_account.current_balance)

    # Build response
    categories_out = []
    for cat in shop.categories:
        cat_items = [
            MenuItemOut.model_validate(it) for it in cat.items if it.is_available
        ]
        categories_out.append(
            MenuCategoryOut(
                id=cat.id,
                name=cat.name,
                sort_order=cat.sort_order,
                items=cat_items
            )
        )

    all_items = [MenuItemOut.model_validate(it) for it in shop.items if it.is_available]

    return ShopDetailOut(
        id=shop.id,
        name=shop.name,
        slug=shop.slug,
        image_url=shop.image_url,
        category=shop.category,
        location_details=shop.location_details,
        phone=shop.phone,
        is_open=shop.is_open,
        prep_lead_time_mins=shop.prep_lead_time_mins,
        settlement_type=shop.settlement_type,
        categories=categories_out,
        items=all_items,
        current_prepaid_balance=prepaid_bal
    )

