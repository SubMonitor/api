from src.api.root import *
from src.api.auth import *
from src.api.me import *
from src.api.subs import *

__all__ = ["api_router", "health_check"]

from src.core import config


def include_routers(app):
    app.include_router(api_router, prefix=config.api_v1_prefix)
    app.include_router(api_auth_router, prefix=config.api_v1_prefix)
    app.include_router(api_me_router, prefix=config.api_v1_prefix)
    app.include_router(api_subs_router, prefix=config.api_v1_prefix)