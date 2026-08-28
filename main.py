# =============================================================
# main.py — API RCS (Twenty Four Seven) — versão CLOUD (Supabase)
# =============================================================
import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from cache import get_dados, get_filiais, get_produtos, invalidar_cache, _store
from routers import vendas, filtros
from security import get_api_key
from supabase_client import executar_query


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("API RCS (cloud) iniciada - pre-carregando caches...")
    asyncio.create_task(get_dados())
    asyncio.create_task(get_filiais(executar_query, "filiais_ref"))
    asyncio.create_task(get_produtos(executar_query, "produtos_ref"))
    yield
    print("API RCS (cloud) encerrada")


app = FastAPI(
    title="API RCS — Twenty Four Seven (Cloud)",
    version="1.0.0",
    description="API dedicada para dashboards de vendas e projeções, servida a partir do Supabase.",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENV") == "dev" else None,
    redoc_url=None,
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

app.include_router(vendas.router, prefix="/api/vendas", tags=["Vendas"])
app.include_router(filtros.router, prefix="/api/filtros", tags=["Filtros"])


@app.get("/api/health", tags=["Health"])
async def health():
    return {"status": "ok", "api": "RCS Twenty Four Seven (cloud)"}


@app.get("/api/cache/refresh", tags=["Cache"])
async def refresh_cache(_key: str = Depends(get_api_key)):
    """Força atualização do cache manualmente (dados de vendas)."""
    invalidar_cache()
    asyncio.create_task(get_dados())  # recarrega em background
    return {"status": "ok", "message": "Cache sendo recarregado em background."}


@app.get("/api/cache/status", tags=["Cache"])
async def cache_status():
    if _store["timestamp"]:
        idade = (datetime.now() - _store["timestamp"]).seconds // 60
        return {
            "status": "ok",
            "registros": len(_store["data"]) if _store["data"] else 0,
            "idade_minutos": idade,
            "loading": _store["loading"],
        }
    return {"status": "vazio", "loading": _store["loading"]}