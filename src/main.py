import fastapi
from starlette.middleware.cors import CORSMiddleware

import src.api
from src.api import *
from src.core import *

setup_logging()
logger = get_logger(__name__)

app = fastapi.FastAPI(title=config.project_name,
                      version=config.version,
                      openapi_url=f"{config.api_v1_prefix}/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

src.api.include_routers(app)
