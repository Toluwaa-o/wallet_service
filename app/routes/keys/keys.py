from fastapi import APIRouter, HTTPException, Depends
from app.models.models import RolloverApiKeyRequest, ApiKeyResponse, CreateApiKeyRequest
from app.utils.utils import get_current_user, get_db, convert_expiry
from app.schemas.schemas import ApiKey
from app.db.connectDB import get_db
from sqlalchemy.orm import Session
from datetime import datetime
from dotenv import load_dotenv
import secrets
import hashlib

load_dotenv()

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post("/create", response_model=ApiKeyResponse)
async def create_api_key(
    req: CreateApiKeyRequest,
    current_user: tuple = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API key"""
    user_id, _ = current_user

    active_keys = db.query(ApiKey).filter(
        ApiKey.user_id == user_id,
        ApiKey.revoked == False,
        ApiKey.expires_at > datetime.utcnow()
    ).count()

    if active_keys >= 5:
        raise HTTPException(
            status_code=400, detail="Maximum 5 active API keys allowed")

    raw_key = f"sk_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    expires_at = convert_expiry(req.expiry)

    api_key = ApiKey(
        id=secrets.token_hex(8),
        user_id=user_id,
        key_hash=key_hash,
        name=req.name,
        permissions=",".join(req.permissions),
        expires_at=expires_at
    )
    db.add(api_key)
    db.commit()

    return ApiKeyResponse(api_id=api_key.id, api_key=raw_key, expires_at=expires_at)


@router.post("/keys/rollover", response_model=ApiKeyResponse)
async def rollover_api_key(
    req: RolloverApiKeyRequest,
    current_user: tuple = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rollover an expired API key"""
    user_id, _ = current_user

    expired_key = db.query(ApiKey).filter(
        ApiKey.id == req.expired_key_id,
        ApiKey.user_id == user_id
    ).first()

    if not expired_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if expired_key.revoked:
        raise HTTPException(
            status_code=400, detail="Cannot rollover a revoked API key")

    if expired_key.expires_at > datetime.utcnow():
        raise HTTPException(status_code=400, detail="API key must be expired")

    raw_key = f"sk_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    expires_at = convert_expiry(req.expiry)

    new_key = ApiKey(
        id=secrets.token_hex(8),
        user_id=user_id,
        key_hash=key_hash,
        name=expired_key.name,
        permissions=expired_key.permissions,
        expires_at=expires_at
    )
    db.add(new_key)

    expired_key.revoked = True

    db.commit()

    return ApiKeyResponse(api_id=new_key.id, api_key=raw_key, expires_at=expires_at)


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    current_user: tuple = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    user_id, _ = current_user

    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == user_id
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if api_key.revoked:
        raise HTTPException(
            status_code=400, detail="API key is already revoked")

    api_key.revoked = True
    db.commit()

    return {"status": "success", "message": "API key revoked"}
