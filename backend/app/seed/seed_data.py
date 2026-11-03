import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import AsyncSessionLocal, engine, Base
from backend.app.models.models import (
    User, EmployeeProfile, DeliveryPartner, UserRole,
    Shop, MenuCategory, MenuItem, SettlementType,
    ShopPrepaidAccount, ShopPrepaidLedger, ShopOperatingHour,
    ShopOnboardingStatus
)

async def seed_database(db: AsyncSession):
    # Check if already seeded
    existing_user = await db.execute(select(User).where(User.phone == "+919876543210"))
    if existing_user.scalar_one_or_none():
        print("Database already contains seed data. Skipping.")
        return

    print("Seeding AtDesk database for JMD Megapolis, Sector 48, Gurugram...")

    # 1. Seed Users
    # Employee
    emp_user = User(
        phone="+919876543210",
        full_name="Aarav Sharma",
        email="aarav.sharma@techcorp.com",
        role=UserRole.EMPLOYEE,
        is_active=True
    )
    db.add(emp_user)
    await db.flush()

    emp_profile = EmployeeProfile(
        user_id=emp_user.id,
        company_name="Zeta Global Technologies",
        tower="Tower B",
        floor=6,
        desk_location="Desk B-612 (Near South Wing)",
        official_id_verified=True
    )
    db.add(emp_profile)

    # Delivery Partner
    runner_user = User(
        phone="+919811122233",
        full_name="Deepak Kumar",
        email="deepak.runner@atdesk.in",
        role=UserRole.DELIVERY_PARTNER,
        is_active=True
    )
    db.add(runner_user)
    await db.flush()

    runner_profile = DeliveryPartner(
        user_id=runner_user.id,
        vehicle_number="HR26-RUNNER-04",
        is_active=True,
        is_available=True,
        current_lat=28.4162,
        current_lng=77.0425,
        battery_percentage=92
    )
    db.add(runner_profile)

    # Admin
    admin_user = User(
        phone="+919999900000",
        full_name="Operations Admin",
        email="admin@thesortedclub.com",
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin_user)
    await db.flush()

    # 2. Seed Shops
    shops_data = [
        {
            "name": "Chaayos - JMD Megapolis",
            "slug": "chaayos-jmd",
            "image_url": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600&auto=format&fit=crop&q=80",
            "category": "Beverages & Snacks",
            "location_details": "Ground Concourse, Near Tower A Entrance",
            "phone": "+919810111222",
            "is_open": True,
            "prep_lead_time_mins": 8,
            "settlement_type": SettlementType.DAILY,
            "categories": [
                {
                    "name": "Chai & Warm Drinks",
                    "sort_order": 1,
                    "items": [
                        {
                            "name": "Desi Chai (Cardamom & Ginger)",
                            "desc": "Freshly brewed Indian tea with adrak, elaichi and fresh mint leaves.",
                            "price": 99,
                            "portion": "Regular (250ml)",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 5,
                            "img": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Kulhad Chai",
                            "desc": "Aromatic masala tea served in traditional clay kulhad.",
                            "price": 119,
                            "portion": "Large (300ml)",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 6,
                            "img": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600&auto=format&fit=crop&q=80"
                        }
                    ]
                },
                {
                    "name": "Nashta & Quick Bites",
                    "sort_order": 2,
                    "items": [
                        {
                            "name": "Classic Bun Maska",
                            "desc": "Fresh bakery bun toasted and smothered with generous Amul butter.",
                            "price": 79,
                            "portion": "1 Bun",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 5,
                            "img": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Loaded Samosa Chaat",
                            "desc": "Crushed crispy samosas topped with curd, spicy mint and sweet tamarind chutneys.",
                            "price": 139,
                            "portion": "Serves 1",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 8,
                            "img": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Homestyle Poha",
                            "desc": "Steamed flattened rice tossed with turmeric, mustard seeds, curry leaves & roasted peanuts.",
                            "price": 119,
                            "portion": "Plate (300g)",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 7,
                            "img": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=600&auto=format&fit=crop&q=80"
                        }
                    ]
                }
            ]
        },
        {
            "name": "Subway - JMD Food Plaza",
            "slug": "subway-jmd",
            "image_url": "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=600&auto=format&fit=crop&q=80",
            "category": "Food",
            "location_details": "Central Atrium Food Court, Ground Floor",
            "phone": "+919810222333",
            "is_open": True,
            "prep_lead_time_mins": 12,
            "settlement_type": SettlementType.PREPAID,
            "categories": [
                {
                    "name": "Sub Sandwiches (6-Inch)",
                    "sort_order": 1,
                    "items": [
                        {
                            "name": "Paneer Tikka Sub",
                            "desc": "Spiced cottage cheese cubes toasted on honey oat bread with crunchy lettuce, capsicum and tandoori mayo.",
                            "price": 239,
                            "portion": "6 inch",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 10,
                            "img": "https://images.unsplash.com/photo-1550547660-d9450f859349?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Roasted Chicken Strip Sub",
                            "desc": "Tender chicken strips grilled with herbs, fresh tomatoes, cucumbers and chipotle sauce.",
                            "price": 269,
                            "portion": "6 inch",
                            "is_food": True,
                            "dietary": "NON_VEG",
                            "prep": 12,
                            "img": "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Corn & Peas Sub",
                            "desc": "Sweet corn and green peas patty seasoned with mild peppers and mint mayonnaise.",
                            "price": 199,
                            "portion": "6 inch",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 10,
                            "img": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&auto=format&fit=crop&q=80"
                        }
                    ]
                },
                {
                    "name": "Sides & Cookies",
                    "sort_order": 2,
                    "items": [
                        {
                            "name": "Double Dark Chocolate Cookie",
                            "desc": "Soft-baked chocolate cookie loaded with dark chocolate chips.",
                            "price": 65,
                            "portion": "1 pc",
                            "is_food": True,
                            "dietary": "EGG",
                            "prep": 3,
                            "img": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Iced Lemon Tea (350ml)",
                            "desc": "Refreshing iced tea infused with natural lemon zest.",
                            "price": 75,
                            "portion": "350ml",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 4,
                            "img": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=600&auto=format&fit=crop&q=80"
                        }
                    ]
                }
            ]
        },
        {
            "name": "Haldiram's Express",
            "slug": "haldirams-jmd",
            "image_url": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=600&auto=format&fit=crop&q=80",
            "category": "Food & Snacks",
            "location_details": "Tower C Concourse, Ground Floor",
            "phone": "+919810333444",
            "is_open": True,
            "prep_lead_time_mins": 14,
            "settlement_type": SettlementType.DAILY,
            "categories": [
                {
                    "name": "Delhi Street Specials",
                    "sort_order": 1,
                    "items": [
                        {
                            "name": "Delhi Style Chole Bhature",
                            "desc": "Two hot puffed bhatures served with rich pindi chole, pickle and spiced onions.",
                            "price": 180,
                            "portion": "2 Bhature + Chole",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 12,
                            "img": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Special Raj Kachori",
                            "desc": "Crispy kachori hollowed and stuffed with sprouted lentils, potatoes, bhalla, and sweetened curd.",
                            "price": 145,
                            "portion": "1 pc",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 8,
                            "img": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Mumbai Pav Bhaji",
                            "desc": "Mashed spiced vegetable bhaji finished with a dollop of butter, served with two toasted pavs.",
                            "price": 160,
                            "portion": "2 Pavs + Bhaji",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 10,
                            "img": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=600&auto=format&fit=crop&q=80"
                        }
                    ]
                },
                {
                    "name": "Mithai & Desserts",
                    "sort_order": 2,
                    "items": [
                        {
                            "name": "Bengali Rasgulla (2 Pcs)",
                            "desc": "Spongy cottage cheese dumplings soaked in fragrant light sugar syrup.",
                            "price": 60,
                            "portion": "2 pcs",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 2,
                            "img": "https://images.unsplash.com/photo-1599785209707-a456fc1337bb?w=600&auto=format&fit=crop&q=80"
                        }
                    ]
                }
            ]
        },
        {
            "name": "Blue Tokai Coffee Roasters",
            "slug": "blue-tokai-jmd",
            "image_url": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=600&auto=format&fit=crop&q=80",
            "category": "Beverages",
            "location_details": "Tower A Main Lobby",
            "phone": "+919810444555",
            "is_open": True,
            "prep_lead_time_mins": 10,
            "settlement_type": SettlementType.PREPAID,
            "categories": [
                {
                    "name": "Specialty Coffee",
                    "sort_order": 1,
                    "items": [
                        {
                            "name": "Iced Vietnamese Latte",
                            "desc": "Double espresso poured over chilled milk and sweet condensed milk with crushed ice.",
                            "price": 220,
                            "portion": "350ml",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 5,
                            "img": "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Flat White (Double Ristretto)",
                            "desc": "Steamed micro-foam milk poured over concentrated double shot espresso.",
                            "price": 210,
                            "portion": "240ml",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 6,
                            "img": "https://images.unsplash.com/photo-1577968897966-3d4325b36b61?w=600&auto=format&fit=crop&q=80"
                        },
                        {
                            "name": "Cold Brew Bold",
                            "desc": "Steeped for 18 hours using Attikan Estate beans. Notes of dark chocolate and fig.",
                            "price": 190,
                            "portion": "300ml",
                            "is_food": True,
                            "dietary": "VEG",
                            "prep": 2,
                            "img": "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?w=600&auto=format&fit=crop&q=80"
                        }
                    ]
                },
                {
                    "name": "Artisanal Bakes",
                    "sort_order": 2,
                    "items": [
                        {
                            "name": "French Butter Croissant",
                            "desc": "Flaky, golden, multi-layered French croissant baked with pure butter.",
                            "price": 160,
                            "portion": "1 pc",
                            "is_food": True,
                            "dietary": "EGG",
                            "prep": 4,
                            "img": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600&auto=format&fit=crop&q=80"
                        }
                    ]
                }
            ]
        },
        {
            "name": "Megapolis Desk Essentials",
            "slug": "megapolis-essentials",
            "image_url": "https://images.unsplash.com/photo-1583947215259-38e31be8751f?w=600&auto=format&fit=crop&q=80",
            "category": "Essentials",
            "location_details": "Tower B Service Concourse",
            "phone": "+919810555666",
            "is_open": True,
            "prep_lead_time_mins": 5,
            "settlement_type": SettlementType.PREPAID,
            "categories": [
                {
                    "name": "Cables & Tech Gadgets",
                    "sort_order": 1,
                    "items": [
                        {
                            "name": "Braided Type-C Fast Cable (1m)",
                            "desc": "Supports 65W fast charging, nylon braided tangle-free wire.",
                            "price": 299,
                            "portion": "1 Unit",
                            "is_food": False,
                            "dietary": "NONE",
                            "prep": 3,
                            "img": None
                        },
                        {
                            "name": "Lightning iPhone Cable (1m)",
                            "desc": "MFi certified durable charging & sync cable.",
                            "price": 349,
                            "portion": "1 Unit",
                            "is_food": False,
                            "dietary": "NONE",
                            "prep": 3,
                            "img": None
                        }
                    ]
                },
                {
                    "name": "Desk Care & Stationery",
                    "sort_order": 2,
                    "items": [
                        {
                            "name": "Gel Pens Quick-Dry (Pack of 3)",
                            "desc": "Smooth 0.5mm tip black/blue ink pens.",
                            "price": 75,
                            "portion": "Pack of 3",
                            "is_food": False,
                            "dietary": "NONE",
                            "prep": 2,
                            "img": None
                        },
                        {
                            "name": "Yellow Sticky Notes (3x3 inch)",
                            "desc": "100 sheets per pad, clean adhesive.",
                            "price": 60,
                            "portion": "1 Pad",
                            "is_food": False,
                            "dietary": "NONE",
                            "prep": 2,
                            "img": None
                        },
                        {
                            "name": "Pocket Hand Sanitizer (50ml)",
                            "desc": "70% alcohol antibacterial desk spray.",
                            "price": 50,
                            "portion": "50ml",
                            "is_food": False,
                            "dietary": "NONE",
                            "prep": 2,
                            "img": None
                        },
                        {
                            "name": "Spearmint Fresh Mints",
                            "desc": "Sugar-free breath freshening tablets.",
                            "price": 35,
                            "portion": "Pocket Tin",
                            "is_food": False,
                            "dietary": "VEG",
                            "prep": 2,
                            "img": None
                        }
                    ]
                }
            ]
        }
    ]

    for s_info in shops_data:
        shop = Shop(
            name=s_info["name"],
            slug=s_info["slug"],
            image_url=s_info["image_url"],
            category=s_info["category"],
            location_details=s_info["location_details"],
            phone=s_info["phone"],
            is_open=s_info["is_open"],
            prep_lead_time_mins=s_info["prep_lead_time_mins"],
            settlement_type=s_info["settlement_type"],
            onboarding_status=s_info.get("onboarding_status", ShopOnboardingStatus.CONFIGURED),
            owner_permission_verified=s_info.get("owner_permission_verified", False),
            contract_signed=s_info.get("contract_signed", False),
            kitchen_prep_audited=s_info.get("kitchen_prep_audited", False),
            packaging_standard_verified=s_info.get("packaging_standard_verified", False),
            official_business_partner=s_info.get("official_business_partner", False),
            onboarding_notes=s_info.get("onboarding_notes")
        )
        db.add(shop)
        await db.flush()

        # Add operating hours (Mon-Sun 9am - 9pm)
        for day in range(7):
            hour = ShopOperatingHour(
                shop_id=shop.id,
                day_of_week=day,
                open_time="09:00",
                close_time="21:00",
                is_closed=False
            )
            db.add(hour)

        # If PREPAID, seed prepaid account and initial ledger credit
        if s_info["settlement_type"] == SettlementType.PREPAID:
            account = ShopPrepaidAccount(
                shop_id=shop.id,
                current_balance=Decimal("6500.00"),
                min_threshold_alert=Decimal("1500.00"),
                is_low_balance_alerted=False,
                last_topped_up_at=datetime.now(timezone.utc)
            )
            db.add(account)
            await db.flush()

            ledger = ShopPrepaidLedger(
                shop_id=shop.id,
                account_id=account.id,
                transaction_type="CREDIT_TOPUP",
                amount=Decimal("6500.00"),
                balance_after=Decimal("6500.00"),
                reference_id=f"SEED-TOPUP-{shop.id}",
                notes="Initial advance prepaid deposit for JMD Megapolis launch"
            )
            db.add(ledger)

        # Add categories and items
        for cat_data in s_info["categories"]:
            cat = MenuCategory(
                shop_id=shop.id,
                name=cat_data["name"],
                sort_order=cat_data["sort_order"]
            )
            db.add(cat)
            await db.flush()

            for itm in cat_data["items"]:
                menu_item = MenuItem(
                    shop_id=shop.id,
                    category_id=cat.id,
                    name=itm["name"],
                    description=itm["desc"],
                    price=Decimal(str(itm["price"])),
                    portion_size=itm["portion"],
                    image_url=itm.get("img"),
                    is_food=itm["is_food"],
                    dietary=itm["dietary"],
                    prep_time_mins=itm["prep"],
                    is_available=True
                )
                db.add(menu_item)

    await db.commit()
    print("Seed data successfully injected into AtDesk database.")

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_database(session)

if __name__ == "__main__":
    asyncio.run(main())

