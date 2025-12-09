from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from app.schemas.schemas import User, Wallet
from app.db.connectDB import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.auth.transport.requests
import google.oauth2.id_token
import secrets
import httpx
import jwt
import os

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXPIRY_HOURS = os.getenv("JWT_EXPIRY_HOURS")

router = APIRouter(prefix="/auth/google", tags=["Authentication"])


@router.get("/")
async def google_login():
    """Redirect to Google sign-in"""
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_CLIENT_ID}&response_type=code&scope=openid%20email%20profile&redirect_uri=http://localhost:8000/auth/google/callback"
    return RedirectResponse(url=google_auth_url)


@router.get("/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": "http://localhost:8000/auth/google/callback",
                    "grant_type": "authorization_code"
                }
            )

        token_data = token_response.json()
        id_token = token_data.get("id_token")

        request = google.auth.transport.requests.Request()
        id_info = google.oauth2.id_token.verify_oauth2_token(
            id_token, request, GOOGLE_CLIENT_ID)

        user_id = id_info["sub"]
        email = id_info["email"]
        name = id_info.get("name", "")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, email=email, name=name)
            db.add(user)

            wallet_number = secrets.token_hex(6)
            wallet = Wallet(id=secrets.token_hex(
                8), user_id=user_id, wallet_number=wallet_number)
            db.add(wallet)
            db.commit()

        payload = {
            "sub": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=int(JWT_EXPIRY_HOURS))
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        return {"access_token": token, "token_type": "bearer"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
