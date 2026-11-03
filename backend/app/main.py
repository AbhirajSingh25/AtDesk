from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.core.config import settings
from backend.app.core.database import engine, Base
from backend.app.api import auth, shops, orders, delivery, admin, payments, storage, notifications
from backend.app.seed.seed_data import seed_database
from backend.app.core.database import AsyncSessionLocal

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database connection & tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed default JMD Megapolis data if empty
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AtDesk - A Product of The Sorted Club. Premium multi-vendor office delivery platform for JMD Megapolis, Sector 48, Gurugram.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth.router, prefix="/api")
app.include_router(shops.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(delivery.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(storage.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "product": settings.PROJECT_NAME,
        "brand": settings.PARENT_BRAND,
        "location": settings.LAUNCH_LOCATION,
        "version": settings.VERSION
    }
