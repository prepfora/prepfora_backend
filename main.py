from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from common.exceptions.api_exception import APIException

## ROUTES
from modules.faq.controller import router as faq_controller
## END OF ROUTES



app = FastAPI()

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

app.include_router(faq_controller)