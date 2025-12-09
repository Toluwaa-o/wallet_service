from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.app_routers.v1 import api_router
from app.routes.health.health import router as health_router

app = FastAPI(title="Wallet Service")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


app.include_router(health_router)
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
