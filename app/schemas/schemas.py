from sqlalchemy import Column, String, Float, DateTime, Boolean
from datetime import datetime
from app.db.connectDB import Base
from app.db.connectDB import engine


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    wallet_number = Column(String, unique=True, index=True)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    wallet_id = Column(String, index=True)
    type = Column(String)
    amount = Column(Float)
    status = Column(String, default="pending")
    reference = Column(String, unique=True, index=True, nullable=True)
    recipient_wallet_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    key_hash = Column(String, unique=True)
    name = Column(String)
    permissions = Column(String)
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)
