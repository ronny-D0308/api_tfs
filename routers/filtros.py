# =============================================================
# routers/filtros.py — versão CLOUD (dados vêm do Supabase)
# =============================================================
import logging
from fastapi import APIRouter, Depends
from cache import get_dados, get_filiais, get_produtos

from security import get_api_key
from supabase_client import executar_query

router = APIRouter()
logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────

def _unicos(dados: list[dict], campo: str) -> list:
    return sorted({
        str(r[campo]).strip()
        for r in dados
        if r.get(campo) and str(r[campo]).strip()
    })


async def _buscar_dados() -> list[dict]:
    return await get_dados()


async def _buscar_filiais() -> list[dict]:
    # "filiais_ref" é o nome da tabela já sincronizada no Supabase
    # (equivalente ao resultado de SQL_FILIAIS no ambiente local).
    return await get_filiais(executar_query, "filiais_ref")


async def _buscar_produtos() -> list[dict]:
    # "produtos_ref" é o nome da tabela já sincronizada no Supabase
    # (equivalente ao resultado de SQL_PRODUTOS no ambiente local).
    return await get_produtos(executar_query, "produtos_ref")


# ── endpoints ─────────────────────────────────────────────────

@router.get("/anos")
async def listar_anos(_key: str = Depends(get_api_key)):
    dados = await _buscar_dados()
    anos = sorted({r["ANO"] for r in dados if r.get("ANO")}, reverse=True)
    return {"status": "ok", "data": anos}


@router.get("/meses")
async def listar_meses(_key: str = Depends(get_api_key)):
    dados = await _buscar_dados()
    return {"status": "ok", "data": _unicos(dados, "MES")}


@router.get("/semestres")
async def listar_semestres(_key: str = Depends(get_api_key)):
    dados = await _buscar_dados()
    return {"status": "ok", "data": _unicos(dados, "SEMESTRE")}


@router.get("/filiais")
async def listar_filiais(_key: str = Depends(get_api_key)):
    dados = await _buscar_filiais()
    return {"status": "ok", "total": len(dados), "data": dados}


@router.get("/grupos")
async def listar_grupos(_key: str = Depends(get_api_key)):
    dados = await _buscar_produtos()
    grupos = sorted({
        str(r["GRUPO_PRODUTO"]).strip()
        for r in dados
        if r.get("GRUPO_PRODUTO") and str(r["GRUPO_PRODUTO"]).strip()
    })
    return {"status": "ok", "total": len(grupos), "data": grupos}


@router.get("/subgrupos")
async def listar_subgrupos(_key: str = Depends(get_api_key)):
    dados = await _buscar_produtos()
    vistos = set()
    resultado = []
    for r in dados:
        grupo    = str(r.get("GRUPO_PRODUTO")    or "").strip()
        subgrupo = str(r.get("SUBGRUPO_PRODUTO") or "").strip()
        chave = (grupo, subgrupo)
        if grupo and subgrupo and chave not in vistos:
            vistos.add(chave)
            resultado.append({"grupo_produto": grupo, "subgrupo_produto": subgrupo})
    resultado.sort(key=lambda x: (x["grupo_produto"], x["subgrupo_produto"]))
    return {"status": "ok", "total": len(resultado), "data": resultado}


@router.get("/linhas")
async def listar_linhas(_key: str = Depends(get_api_key)):
    dados = await _buscar_produtos()
    linhas = sorted({
        str(r["LINHA"]).strip()
        for r in dados
        if r.get("LINHA") and str(r["LINHA"]).strip()
    })
    return {"status": "ok", "total": len(linhas), "data": linhas}


@router.get("/origens")
async def listar_origens(_key: str = Depends(get_api_key)):
    dados = await _buscar_dados()
    return {"status": "ok", "data": _unicos(dados, "ORIGEM")}


@router.get("/tipos-operacao")
async def listar_tipos_operacao(_key: str = Depends(get_api_key)):
    dados = await _buscar_dados()
    return {"status": "ok", "data": _unicos(dados, "TIPO")}