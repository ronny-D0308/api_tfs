# cache.py — Cache global compartilhado entre vendas e filtros
from datetime import datetime, timedelta
import asyncio
import logging
from functools import partial
from supabase_client import executar_procedure
logger = logging.getLogger(__name__)

PROCEDURE = "vendas"
CACHE_TTL = timedelta(hours=2)

_store = {"data": None, "timestamp": None, "loading": False}

# cache.py — adicione ao final do arquivo existente

# Cache para filiais
_cache_filiais = {"data": None, "timestamp": None, "loading": False}

# Cache para produtos (grupos, subgrupos, linhas)
_cache_produtos = {"data": None, "timestamp": None, "loading": False}


async def get_filiais(executar_query_fn, sql: str) -> list[dict]:
    global _cache_filiais
    agora = datetime.now()

    if (
        _cache_filiais["data"] is not None
        and _cache_filiais["timestamp"] is not None
        and agora - _cache_filiais["timestamp"] < CACHE_TTL
    ):
        return _cache_filiais["data"]

    if _cache_filiais["loading"]:
        while _cache_filiais["loading"]:
            await asyncio.sleep(0.5)
        return _cache_filiais["data"]

    _cache_filiais["loading"] = True
    try:
        loop = asyncio.get_event_loop()
        dados = await asyncio.wait_for(
            loop.run_in_executor(None, partial(executar_query_fn, sql, ())),
            timeout=300
        )
        _cache_filiais["data"] = dados
        _cache_filiais["timestamp"] = agora
        logger.info(f"Cache filiais carregado com {len(dados)} registros")
        return dados
    finally:
        _cache_filiais["loading"] = False


async def get_produtos(executar_query_fn, sql: str) -> list[dict]:
    global _cache_produtos
    agora = datetime.now()

    if (
        _cache_produtos["data"] is not None
        and _cache_produtos["timestamp"] is not None
        and agora - _cache_produtos["timestamp"] < CACHE_TTL
    ):
        return _cache_produtos["data"]

    if _cache_produtos["loading"]:
        while _cache_produtos["loading"]:
            await asyncio.sleep(0.5)
        return _cache_produtos["data"]

    _cache_produtos["loading"] = True
    try:
        loop = asyncio.get_event_loop()
        dados = await asyncio.wait_for(
            loop.run_in_executor(None, partial(executar_query_fn, sql, ())),
            timeout=300
        )
        _cache_produtos["data"] = dados
        _cache_produtos["timestamp"] = agora
        logger.info(f"Cache produtos carregado com {len(dados)} registros")
        return dados
    finally:
        _cache_produtos["loading"] = False


def invalidar_todos():
    """Limpa todos os caches."""
    _store["data"] = None
    _store["timestamp"] = None
    _cache_filiais["data"] = None
    _cache_filiais["timestamp"] = None
    _cache_produtos["data"] = None
    _cache_produtos["timestamp"] = None


async def get_dados() -> list[dict]:
    """Retorna dados do cache ou executa a procedure uma vez."""
    global _store

    agora = datetime.now()

    # Cache válido — retorna instantaneamente
    if (
        _store["data"] is not None
        and _store["timestamp"] is not None
        and agora - _store["timestamp"] < CACHE_TTL
    ):
        return _store["data"]

    # Aguarda se já está carregando (evita execuções paralelas)
    if _store["loading"]:
        logger.info("Aguardando carregamento em andamento...")
        while _store["loading"]:
            await asyncio.sleep(0.5)
        return _store["data"]

    # Executa a procedure
    logger.info("Carregando dados da procedure...")
    _store["loading"] = True
    try:
        loop = asyncio.get_event_loop()
        dados = await asyncio.wait_for(
            loop.run_in_executor(None, partial(executar_procedure, PROCEDURE)),
            timeout=300
        )
        _store["data"] = dados
        _store["timestamp"] = agora
        logger.info(f"Cache carregado com {len(dados)} registros")
        return dados
    finally:
        _store["loading"] = False


def invalidar_cache():
    """Limpa o cache forçando recarregamento na próxima requisição."""
    _store["data"] = None
    _store["timestamp"] = None