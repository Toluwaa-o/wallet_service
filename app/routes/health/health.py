from fastapi import APIRouter

router = APIRouter(prefix="", tags=["Health"])


@router.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
