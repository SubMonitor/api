from src.api.root.router import api_router

@api_router.get("/health")
async def health_check():
    return {"status": "ok"}
