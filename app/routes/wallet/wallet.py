from fastapi import APIRouter, HTTPException, Depends, Header, Request
from app.schemas.schemas import User, Wallet, Transaction
from app.models.models import WalletBalance, DepositRequest, DepositResponse, PermissionEnum, TransactionResponse, TransferRequest, TransferResponse
from app.utils.utils import get_current_user, get_db, check_permission
from app.db.connectDB import get_db
from sqlalchemy.orm import Session
from typing import Optional, List
from dotenv import load_dotenv
import hashlib
import hmac
import json
import secrets
import httpx
import os

load_dotenv()

PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET")
PAYSTACK_BASE_URL = "https://api.paystack.co"

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.post("/deposit", response_model=DepositResponse)
async def deposit_wallet(
    req: DepositRequest,
    current_user: tuple = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize Paystack deposit"""
    user_id, permissions = current_user
    check_permission(permissions, PermissionEnum.DEPOSIT)

    user = db.query(User).filter(User.id == user_id).first()
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()

    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    reference = f"txn_{secrets.token_hex(8)}"
    transaction = Transaction(
        id=secrets.token_hex(8),
        wallet_id=wallet.id,
        type="deposit",
        amount=req.amount,
        reference=reference,
        status="pending"
    )
    db.add(transaction)
    db.commit()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYSTACK_BASE_URL}/transaction/initialize",
                json={
                    "email": user.email,
                    "amount": int(req.amount * 100),
                    "reference": reference
                },
                headers={"Authorization": f"Bearer {PAYSTACK_SECRET}"},
                timeout=10.0
            )

        response.raise_for_status()
        data = response.json()

        if not data.get("status"):
            transaction.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Failed to initialize payment"
            )

        return DepositResponse(
            reference=reference,
            authorization_url=data["data"]["authorization_url"]
        )

    except httpx.RequestError as e:
        transaction.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=503,
            detail=f"Payment service unavailable: {str(e)}"
        )

    except httpx.HTTPStatusError as e:
        transaction.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Payment service error: {e.response.text}"
        )

    except Exception as e:
        transaction.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Handle Paystack webhook"""
    if not x_paystack_signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    body = await request.body()
    
    hash_obj = hmac.new(
        PAYSTACK_SECRET.encode(),
        body,
        hashlib.sha512
    )
    expected_sig = hash_obj.hexdigest()

    if x_paystack_signature != expected_sig:
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    
    reference = data.get("reference")
    
    print(reference)
    transaction = db.query(Transaction).filter(
        Transaction.reference == reference).first()

    if not transaction:
        return {"status": True}

    print('passed first check')
    if transaction.status == "success":
        return {"status": True}

    print('passed checks')
    if data.get("status"):
        transaction.status = "success"
        wallet = db.query(Wallet).filter(
            Wallet.id == transaction.wallet_id).first()
        wallet.balance += transaction.amount
    else:
        transaction.status = "failed"

    db.commit()
    return {"status": True}


@router.get("/deposit/{reference}/status")
async def deposit_status(
    reference: str,
    current_user: tuple = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get deposit status (does not credit wallet)"""
    user_id, permissions = current_user
    check_permission(permissions, PermissionEnum.READ)

    transaction = db.query(Transaction).filter(
        Transaction.reference == reference).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if transaction.wallet_id != wallet.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to transaction")

    return {
        "reference": reference,
        "status": transaction.status,
        "amount": transaction.amount
    }


@router.get("/balance", response_model=WalletBalance)
async def get_balance(
    current_user: tuple = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get wallet balance"""
    user_id, permissions = current_user
    check_permission(permissions, PermissionEnum.READ)

    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return WalletBalance(balance=wallet.balance)


@router.post("/transfer", response_model=TransferResponse)
async def transfer_funds(
    req: TransferRequest,
    current_user: tuple = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Transfer funds to another wallet"""
    user_id, permissions = current_user
    check_permission(permissions, PermissionEnum.TRANSFER)

    sender_wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    recipient_wallet = db.query(Wallet).filter(
        Wallet.wallet_number == req.wallet_number).first()

    if not sender_wallet or not recipient_wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if sender_wallet.id == recipient_wallet.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot transfer money to your own wallet"
        )

    if sender_wallet.balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    sender_wallet.balance -= req.amount
    recipient_wallet.balance += req.amount

    for wallet, t_type in [(sender_wallet, "transfer_out"), (recipient_wallet, "transfer_in")]:
        transaction = Transaction(
            id=secrets.token_hex(8),
            wallet_id=wallet.id,
            type="transfer",
            amount=req.amount,
            status="success",
            recipient_wallet_id=recipient_wallet.id if t_type == "transfer_out" else sender_wallet.id
        )
        db.add(transaction)

    db.commit()
    return TransferResponse(status="success", message="Transfer completed")


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    current_user: tuple = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get transaction history"""
    user_id, permissions = current_user
    check_permission(permissions, PermissionEnum.READ)

    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    transactions = db.query(Transaction).filter(
        Transaction.wallet_id == wallet.id).all()

    return [
        TransactionResponse(type=t.type, amount=t.amount, status=t.status)
        for t in transactions
    ]
