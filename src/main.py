import asyncio
from contextlib import asynccontextmanager

import fastapi
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

import src.api
from src.api import *
from src.core import *
from src.db import engine, Base

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    #начало
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Код при завершении работы



logger = get_logger(__name__)

app = fastapi.FastAPI(title=config.project_name,
                      version=config.version,
                      openapi_url=f"{config.api_v1_prefix}/openapi.json",
                      lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
src.api.include_routers(app)
