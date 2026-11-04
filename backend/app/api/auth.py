from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import Optional
import logging

from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, get_current_user
from backend.app.models.models import User, EmployeeProfile, DeliveryPartner, ShopStaffProfile, UserRole
from backend.app.schemas.schemas import (
    OTPRequest, OTPVerify, EmployeeRegisterRequest, ShopStaffRegisterRequest, UserOut, TokenResponse
)
from backend.app.services.sms_service import SmsService

logger = logging.getLogger("atdesk.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])

def build_user_out(user: User) -> UserOut:
    shop_id = user.shop_staff_profile.shop_id if user.shop_staff_profile else None
    return UserOut(
        id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        company_name=user.employee_profile.company_name if user.employee_profile else None,
        tower=user.employee_profile.tower if user.employee_profile else None,
        floor=user.employee_profile.floor if user.employee_profile else None,
        desk_location=user.employee_profile.desk_location if user.employee_profile else None,
        shop_id=shop_id
    )

@router.post("/send-otp")
async def send_otp(request: OTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Indian DLT-compliant SMS OTP dispatch for JMD Megapolis employee, runner, and vendor staff logins.
    Enforces 60-second cooldown, 5-minute validity, rate limiting, and template validation.
    """
    try:
        result = SmsService.generate_and_send_otp(request.phone)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    if not result.get("success"):
        error_code = result.get("error")
        if error_code == "COOLDOWN_ACTIVE":
            raise HTTPException(status_code=429, detail=result["message"])
        elif error_code in ["RATE_LIMIT_EXCEEDED", "LOCKED_OUT"]:
            raise HTTPException(status_code=429, detail=result["message"])
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    return result

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(request: OTPVerify, db: AsyncSession = Depends(get_db)):
    """
    Verify phone OTP against Indian DLT security service and return JWT access token.
    Enforces maximum 3 attempts and invalidates used OTPs.
    """
    clean_phone = request.phone.strip()
    
    # Verify OTP through SmsService
    verification = SmsService.verify_otp(clean_phone, request.otp)
    if not verification.get("success"):
        raise HTTPException(status_code=400, detail=verification["message"])

    # Locate or create user account
    normalized_digits = SmsService._normalize_phone(clean_phone)
    stmt = (
        select(User)
        .options(
            selectinload(User.employee_profile), 
            selectinload(User.delivery_profile),
            selectinload(User.shop_staff_profile)
        )
        .where(User.phone.like(f"%{normalized_digits}%"))
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        # Create user account
        user = User(
            phone=f"+91{normalized_digits}",
            full_name=f"User ({normalized_digits[-4:]})",
            email=f"user_{normalized_digits[-4:]}@jmdmegapolis.in",
            role=request.role or UserRole.EMPLOYEE,
            is_active=True
        )
        db.add(user)
        await db.flush()

        if user.role == UserRole.EMPLOYEE:
            profile = EmployeeProfile(
                user_id=user.id,
                company_name="JMD Tech Hub",
                tower="Tower B",
                floor=4,
                desk_location="Desk B-402",
                official_id_verified=True
            )
            db.add(profile)
            await db.flush()
        elif user.role == UserRole.DELIVERY_PARTNER:
            runner = DeliveryPartner(
                user_id=user.id,
                vehicle_number="HR26-RUNNER-NEW",
                is_active=True,
                is_available=True,
                current_lat=28.4162,
                current_lng=77.0425
            )
            db.add(runner)
            await db.flush()

        await db.commit()
        # Reload user with profile
        stmt = (
            select(User)
            .options(
                selectinload(User.employee_profile), 
                selectinload(User.delivery_profile),
                selectinload(User.shop_staff_profile)
            )
            .where(User.id == user.id)
        )
        user = (await db.execute(stmt)).scalar_one()

    token = create_access_token({
        "sub": str(user.id), 
        "phone": user.phone, 
        "role": user.role.value
    })

    return TokenResponse(access_token=token, user=build_user_out(user))

@router.get("/me", response_model=UserOut)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Fetch profile of currently authenticated user"""
    return build_user_out(current_user)

@router.post("/register-employee", response_model=TokenResponse)
async def register_employee(request: EmployeeRegisterRequest, db: AsyncSession = Depends(get_db)):
    """JMD Megapolis Employee Registration"""
    try:
        normalized_digits = SmsService._normalize_phone(request.phone)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    phone_full = f"+91{normalized_digits}"
    stmt = (
        select(User)
        .options(
            selectinload(User.employee_profile),
            selectinload(User.delivery_profile),
            selectinload(User.shop_staff_profile)
        )
        .where(User.phone.like(f"%{normalized_digits}%"))
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.full_name = request.full_name
        existing.email = request.email
        if existing.employee_profile:
            existing.employee_profile.company_name = request.company_name
            existing.employee_profile.tower = request.tower
            existing.employee_profile.floor = request.floor
            existing.employee_profile.desk_location = request.desk_location
        user = existing
    else:
        user = User(
            phone=phone_full,
            full_name=request.full_name,
            email=request.email,
            role=UserRole.EMPLOYEE,
            is_active=True
        )
        db.add(user)
        await db.flush()

        profile = EmployeeProfile(
            user_id=user.id,
            company_name=request.company_name,
            tower=request.tower,
            floor=request.floor,
            desk_location=request.desk_location,
            official_id_verified=True
        )
        db.add(profile)

    await db.commit()

    # Reload user with relationships loaded
    stmt = (
        select(User)
        .options(
            selectinload(User.employee_profile),
            selectinload(User.delivery_profile),
            selectinload(User.shop_staff_profile)
        )
        .where(User.id == user.id)
    )
    user = (await db.execute(stmt)).scalar_one()

    token = create_access_token({"sub": str(user.id), "phone": user.phone, "role": user.role.value})
    return TokenResponse(access_token=token, user=build_user_out(user))

@router.post("/register", response_model=TokenResponse, include_in_schema=False)
async def register_legacy_alias(request: EmployeeRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_employee(request, db)

@router.post("/register-shop-staff", response_model=TokenResponse)
async def register_shop_staff(request: ShopStaffRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register staff member for Shop Order Inbox"""
    try:
        normalized_digits = SmsService._normalize_phone(request.phone)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    phone_full = f"+91{normalized_digits}"
    stmt = (
        select(User)
        .options(
            selectinload(User.employee_profile),
            selectinload(User.delivery_profile),
            selectinload(User.shop_staff_profile)
        )
        .where(User.phone.like(f"%{normalized_digits}%"))
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.full_name = request.full_name
        existing.role = UserRole.SHOP_STAFF
        if existing.shop_staff_profile:
            existing.shop_staff_profile.shop_id = request.shop_id
            existing.shop_staff_profile.role_title = request.role_title
        else:
            profile = ShopStaffProfile(
                user_id=existing.id,
                shop_id=request.shop_id,
                role_title=request.role_title
            )
            db.add(profile)
        user = existing
    else:
        user = User(
            phone=phone_full,
            full_name=request.full_name,
            role=UserRole.SHOP_STAFF,
            is_active=True
        )
        db.add(user)
        await db.flush()

        profile = ShopStaffProfile(
            user_id=user.id,
            shop_id=request.shop_id,
            role_title=request.role_title
        )
        db.add(profile)

    await db.commit()

    # Reload user with relationships loaded
    stmt = (
        select(User)
        .options(
            selectinload(User.employee_profile),
            selectinload(User.delivery_profile),
            selectinload(User.shop_staff_profile)
        )
        .where(User.id == user.id)
    )
    user = (await db.execute(stmt)).scalar_one()

    token = create_access_token({"sub": str(user.id), "phone": user.phone, "role": user.role.value})
    return TokenResponse(access_token=token, user=build_user_out(user))
