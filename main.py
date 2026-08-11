from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from common.exceptions.api_exception import APIException
from contextlib import asynccontextmanager
from common.database import Base, engine
from dotenv import load_dotenv
load_dotenv()

## ROUTES IMPORT
from modules.faq.faq_controller import router as faq_controller
from modules.waitlist.controller import router as waitlist_controller
from modules.contact_message.controller import router as contact_message_controller
## END OF ROUTES

### Database initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(
    title="Prefora Backend API",
    description="API documentation for Prefora Backend services.",
    version="1.0.0",
    lifespan=lifespan,
)

### API Exception Handler
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

### Validation Exception Handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    # Extract the clean error message (removes Pydantic's "Value error, " prefix if present)
    msg = errors[0].get("msg", "Validation error").replace("Value error, ", "") if errors else "Validation error"

    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": msg,
            "data": None,
            "pagination": None,
        },
    )


### HEALTH REGISTRATION
@app.get("/health")
async def health():
    return {
        "status": "ok"
    }

### ROUTE REGISTRATION
app.include_router(faq_controller)
app.include_router(waitlist_controller)
app.include_router(contact_message_controller)