from app.models.models import ExpiryEnum
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, Depends, Header
from app.schemas.schemas import ApiKey
from app.models.models import PermissionEnum
from app.db.connectDB import get_db
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import hashlib
import jwt
import os

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXPIRY_HOURS = os.getenv("JWT_EXPIRY_HOURS")


def convert_expiry(expiry: ExpiryEnum) -> datetime:
    """Convert expiry string to datetime"""
    now = datetime.utcnow()
    if expiry == ExpiryEnum.ONE_HOUR:
        return now + timedelta(hours=1)
    elif expiry == ExpiryEnum.ONE_DAY:
        return now + timedelta(days=1)
    elif expiry == ExpiryEnum.ONE_MONTH:
        return now + timedelta(days=30)
    elif expiry == ExpiryEnum.ONE_YEAR:
        return now + timedelta(days=365)


def get_user_from_token(authorization: Optional[str] = Header(None)) -> str:
    """Extract and verify JWT token"""
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Missing authorization header")

    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_api_key_user(x_api_key: Optional[str] = Header(None), db: Session = Depends(get_db)) -> tuple[str, list]:
    """Extract and verify API key"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()

    api_key_record = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.revoked == False,
        ApiKey.expires_at > datetime.utcnow()
    ).first()

    if not api_key_record:
        raise HTTPException(
            status_code=401, detail="Invalid or expired API key")

    permissions = api_key_record.permissions.split(",")
    return api_key_record.user_id, permissions


def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> tuple[str, List[str]]:
    """Get current user from JWT or API key"""
    if authorization:
        user_id = get_user_from_token(authorization)
        return user_id, [PermissionEnum.DEPOSIT, PermissionEnum.TRANSFER, PermissionEnum.READ]

    if x_api_key:
        return get_api_key_user(x_api_key, db)

    raise HTTPException(status_code=401, detail="Missing authentication")


def check_permission(permissions: List[str], required: str):
    """Check if user has required permission"""
    if required not in permissions:
        raise HTTPException(
            status_code=403, detail=f"Missing permission: {required}")
