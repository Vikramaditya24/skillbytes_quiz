from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, catalog, quiz
from app.core.config import settings
from app.core.db import close_client, create_indexes, get_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes(get_database())
    yield
    await close_client()


app = FastAPI(title="Skillbytes Quiz API", version="1.0.0", lifespan=lifespan)

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(quiz.router)
app.include_router(analytics.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
