# =============================================================
# main.py — API RCS (Dedicada Twenty Four Seven)
# =============================================================

from cache import get_dados, invalidar_cache
import asyncio
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from routers import vendas, filtros
from security import get_api_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    from database import executar_query
    from cache import get_dados, get_filiais, get_produtos
    from routers.filtros import SQL_FILIAIS, SQL_PRODUTOS
    print("✅ API RCS iniciada — pré-carregando caches...")
    asyncio.create_task(get_dados())
    asyncio.create_task(get_filiais(executar_query, SQL_FILIAIS))
    asyncio.create_task(get_produtos(executar_query, SQL_PRODUTOS))
    yield
    print("🔴 API RCS encerrada")

app = FastAPI(
    title="API RCS — Twenty Four Seven",
    version="1.0.0",
    description="API dedicada para dashboards de vendas e projeções.",
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
    return {"status": "ok", "api": "RCS Twenty Four Seven"}

@app.get("/api/cache/refresh", tags=["Cache"])
async def refresh_cache(_key: str = Depends(get_api_key)):
    """Força atualização do cache manualmente."""
    from routers.vendas import _cache
    _cache["data"] = None
    _cache["timestamp"] = None
    return {"status": "ok", "message": "Cache limpo. Próxima requisição recarregará os dados."}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ API RCS iniciada — pré-carregando cache...")
    asyncio.create_task(get_dados())  # carrega em background ao subir
    yield
    print("🔴 API RCS encerrada")

@app.get("/api/cache/refresh", tags=["Cache"])
async def refresh_cache(_key: str = Depends(get_api_key)):
    invalidar_cache()
    asyncio.create_task(get_dados())  # recarrega em background
    return {"status": "ok", "message": "Cache sendo recarregado em background."}

@app.get("/api/cache/status", tags=["Cache"])
async def cache_status():
    from cache import _store
    from datetime import datetime
    if _store["timestamp"]:
        idade = (datetime.now() - _store["timestamp"]).seconds // 60
        return {
            "status": "ok",
            "registros": len(_store["data"]) if _store["data"] else 0,
            "idade_minutos": idade,
            "loading": _store["loading"]
        }
    return {"status": "vazio", "loading": _store["loading"]}