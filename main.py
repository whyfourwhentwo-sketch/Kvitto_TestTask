from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

import models  # noqa: F401  (чтобы Payment попал в metadata)
from api import router
from db import Base, engine
from errors import InvalidPromo, InvalidTransition, PaymentNotFound


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.exception_handler(PaymentNotFound)
async def payment_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "payment not found"})


@app.exception_handler(InvalidPromo)
async def invalid_promo(request, exc):
    return JSONResponse(status_code=422, content={"detail": "invalid promo code"})


@app.exception_handler(InvalidTransition)
async def invalid_transition(request, exc):
    return JSONResponse(status_code=409, content={"error": "invalid_transition"})