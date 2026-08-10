from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from common.exceptions.api_exception import APIException
from contextlib import asynccontextmanager
from common.database import Base, engine, get_db
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
load_dotenv()

## ROUTES
from modules.faq.faq_controller import router as faq_controller
## END OF ROUTES

### Database initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
app = FastAPI(lifespan=lifespan)

### Exception Handler
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "data": exc.data,
            "pagination": exc.pagination,
        },
    )

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }

app.include_router(faq_controller)