# Wallet Service API

A FastAPI-based wallet service with Paystack integration, JWT authentication, and API key management for secure wallet operations.

## Features

- **Google OAuth** - Sign in with Google and receive JWT tokens
- **Paystack Deposits** - Accept payments via Paystack with webhook verification
- **Wallet Transfers** - Transfer funds between user wallets atomically
- **API Keys** - Service-to-service authentication with permissions and expiry
- **Transaction History** - Track all wallet activities
- **Permission-based Access** - Granular control over API key capabilities

## Prerequisites

- Python 3.8+
- PostgreSQL or SQLite
- Paystack account (secret key)
- Google OAuth credentials

## Installation

```bash
uv sync

# Set environment variables
export DATABASE_URL="sqlite:///./wallet.db"
export PAYSTACK_SECRET_KEY="sk_live_xxxxx"
export GOOGLE_CLIENT_ID="your_client_id"
export GOOGLE_CLIENT_SECRET="your_client_secret"
export JWT_SECRET="your_secret_key"
export JWT_ALGORITHM='####'
export JWT_EXPIRY_HOURS='1Y'

# Run server
uvicorn app.main:app --reload
```

## API Endpoints

### Authentication
- `GET /auth/google` - Redirect to Google sign-in
- `GET /auth/google/callback` - OAuth callback (returns JWT)

### API Keys
- `POST /keys/create` - Create new API key with permissions
- `POST /keys/rollover` - Rollover expired API key
- `POST /keys/{key_id}/revoke` - Revoke an API key

### Wallet Operations
- `POST /wallet/deposit` - Initialize Paystack deposit
- `POST /wallet/paystack/webhook` - Paystack webhook handler
- `GET /wallet/deposit/{reference}/status` - Check deposit status
- `GET /wallet/balance` - Get wallet balance
- `POST /wallet/transfer` - Transfer funds to another wallet
- `GET /wallet/transactions` - Get transaction history

## Authentication

Use either JWT or API Key in requests:

```bash
# JWT (from Google sign-in)
Authorization: Bearer <jwt_token>

# API Key (service-to-service)
x-api-key: <api_key>
```

## API Key Permissions

- `deposit` - Initialize deposits
- `transfer` - Transfer funds
- `read` - View balance and history

Maximum 5 active keys per user. Expiry options: `1H`, `1D`, `1M`, `1Y`

## Key Features

✅ Atomic wallet transfers (no partial deductions)  
✅ Idempotent webhook processing (no double-credits)  
✅ Paystack signature validation  
✅ Automatic API key expiry enforcement  
✅ Transaction status tracking  
✅ Error handling with transaction rollback  

## Example Usage

```bash
# Sign in with Google
curl http://localhost:8000/auth/google

# Create API Key
curl -X POST http://localhost:8000/keys/create \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"service-key","permissions":["deposit","transfer","read"],"expiry":"1M"}'

# Deposit
curl -X POST http://localhost:8000/wallet/deposit \
  -H "Authorization: Bearer <jwt>" \
  -d '{"amount":5000}'

# Transfer funds
curl -X POST http://localhost:8000/wallet/transfer \
  -H "Authorization: Bearer <jwt>" \
  -d '{"wallet_number":"4566678954356","amount":3000}'
```

## Security

- API keys are hashed
- JWT tokens expire after 24 hours
- Paystack webhooks are signature-validated
- All sensitive operations require authentication
- API keys are limited to 5 per user

## Database Models

- **User** - User information from Google sign-in
- **Wallet** - User wallet with balance
- **Transaction** - Deposit and transfer records
- **ApiKey** - API keys with permissions and expiry