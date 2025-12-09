from pydantic import BaseModel, Field
from enum import Enum
from typing import List
from datetime import datetime


class PermissionEnum(str, Enum):
    DEPOSIT = "deposit"
    TRANSFER = "transfer"
    READ = "read"


class ExpiryEnum(str, Enum):
    ONE_HOUR = "1H"
    ONE_DAY = "1D"
    ONE_MONTH = "1M"
    ONE_YEAR = "1Y"


class GoogleTokenRequest(BaseModel):
    token: str


class CreateApiKeyRequest(BaseModel):
    name: str
    permissions: List[PermissionEnum]
    expiry: ExpiryEnum


class RolloverApiKeyRequest(BaseModel):
    expired_key_id: str
    expiry: ExpiryEnum


class DepositRequest(BaseModel):
    amount: float = Field(gt=0)


class TransferRequest(BaseModel):
    wallet_number: str
    amount: float = Field(gt=0)


class ApiKeyResponse(BaseModel):
    api_id: str
    api_key: str
    expires_at: datetime


class DepositResponse(BaseModel):
    reference: str
    authorization_url: str


class WalletBalance(BaseModel):
    balance: float


class TransactionResponse(BaseModel):
    type: str
    amount: float
    status: str


class TransferResponse(BaseModel):
    status: str
    message: str
