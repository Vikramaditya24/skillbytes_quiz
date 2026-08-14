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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
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
