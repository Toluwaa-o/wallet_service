from app.routes.auth.auth import router as auth_router
from app.routes.keys.keys import router as key_router
from app.routes.wallet.wallet import router as wallet_router
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(key_router)
api_router.include_router(wallet_router)
