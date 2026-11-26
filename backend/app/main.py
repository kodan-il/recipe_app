from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import recipes

def create_app() -> FastAPI:
    app = FastAPI(title="Recipe Engine API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(recipes.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str,str]:
        return {"status": "ok"}
    
    return app

app = create_app()