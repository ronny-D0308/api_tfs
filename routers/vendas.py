import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from functools import partial
from cache import get_dados
from datetime import datetime, timedelta

from security import get_api_key

router = APIRouter()
logger = logging.getLogger(__name__)

PROCEDURE = "P_RCS_REPORT_PROJECAO_2026"
TIMEOUT = 300  # 5 minutos

# Cache em memória
_cache = {"data": None, "timestamp": None}
CACHE_TTL = timedelta(minutes=30)


async def _buscar_dados() -> list[dict]:
    return await get_dados()


def _aplicar_filtros(dados: list[dict], filtros: dict) -> list[dict]:
    for campo, valor in filtros.items():
        if valor is not None and str(valor).strip() not in ("", "Todos", "Todas"):
            # Suporta múltiplos valores separados por vírgula ou parâmetros repetidos (lista)
            if isinstance(valor, list):
                valores = [str(v).replace("+", " ").strip() for v in valor if v]
            else:
                valores = [v.replace("+", " ").strip() for v in str(valor).split(",") if v.strip()]
            
            valores = [v for v in valores if v not in ("Todos", "Todas", "")]
            
            if valores:
                dados = [
                    r for r in dados
                    if str(r.get(campo, "") or "").strip() in valores
                ]
    return dados


def _safe_float(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


@router.get("/comparativo-mensal")
async def comparativo_mensal(
    ano_atual:    int           = Query(default=2026),
    ano_anterior: int           = Query(default=2025),
    filial:       Optional[str] = Query(default=None),
    grupo:        Optional[str] = Query(default=None),
    subgrupo:     Optional[str] = Query(default=None),
    linha:        Optional[str] = Query(default=None),
    semestre:     Optional[str] = Query(default=None),
    origem:       Optional[str] = Query(default=None),
    mes:          Optional[str] = Query(default=None),
    canal: Optional[str] = Query(default=None),
    _key: str = Depends(get_api_key)
):
    dados = await _buscar_dados()
    dados = _aplicar_filtros(dados, {
        "FILIAL":           filial,
        "GRUPO_PRODUTO":    grupo,
        "SUBGRUPO_PRODUTO": subgrupo,
        "LINHA":            linha,
        "SEMESTRE":         semestre,
        "ORIGEM":           origem,
        "TIPO_FILIAL":      canal,   # ← canal mapeia para TIPO_FILIAL
    })

    meses: dict[str, dict] = {}
    for row in dados:
        ano = row.get("ANO")
        mes_row = str(row.get("MES") or "").strip()
        if not mes_row or ano not in (ano_atual, ano_anterior):
            continue

        if mes_row not in meses:
            meses[mes_row] = {
                "mes": mes_row,
                "semestre": row.get("SEMESTRE"),
                "venda_ano_atual": 0.0,
                "venda_ano_anterior": 0.0,
                "crescimento_2026": 0.0,
            }

        venda = _safe_float(row.get("VENDA_LIQUIDA"))
        cresc = _safe_float(row.get("CRESCIMENTO_2026"))

        if ano == ano_atual:
            meses[mes_row]["venda_ano_atual"]  += venda
            meses[mes_row]["crescimento_2026"] += cresc
        elif ano == ano_anterior:
            meses[mes_row]["venda_ano_anterior"] += venda

    resultado = []
    for item in sorted(meses.values(), key=lambda x: x["mes"]):
        ant = item["venda_ano_anterior"]
        atu = item["venda_ano_atual"]
        item["percentual_crescimento"] = (
            round((atu - ant) / ant * 100, 2) if ant != 0 else None
        )
        resultado.append(item)

    # Filtro de mês aplicado APÓS agregar
    if mes and mes.strip() not in ("", "Todos", "Todas"):
        meses_selecionados = [m.strip() for m in mes.split(",")]
        resultado = [r for r in resultado if r["mes"] in meses_selecionados]

    return {"status": "ok", "total": len(resultado), "data": resultado}


@router.get("/comparativo-loja")
async def comparativo_loja(
    ano_atual:    int           = Query(default=2026),
    ano_anterior: int           = Query(default=2025),
    mes:          Optional[str] = Query(default=None),
    semestre:     Optional[str] = Query(default=None),
    grupo:        Optional[str] = Query(default=None),
    subgrupo:     Optional[str] = Query(default=None),
    linha:        Optional[str] = Query(default=None),
    origem:       Optional[str] = Query(default=None),
    _key: str = Depends(get_api_key)
):
    dados = await _buscar_dados()
    dados = _aplicar_filtros(dados, {
        "MES": mes, "SEMESTRE": semestre,
        "GRUPO_PRODUTO": grupo, "SUBGRUPO_PRODUTO": subgrupo,
        "LINHA": linha, "ORIGEM": origem,
    })

    lojas: dict[str, dict] = {}
    for row in dados:
        ano    = row.get("ANO")
        filial = str(row.get("FILIAL") or "").strip()
        if not filial or ano not in (ano_atual, ano_anterior):
            continue

        if filial not in lojas:
            lojas[filial] = {
                "filial": filial,
                "tipo_filial": row.get("TIPO_FILIAL"),
                "codigo_filial": row.get("CODIGO_FILIAL"),
                "venda_ano_atual": 0.0,
                "venda_ano_anterior": 0.0,
                "crescimento_2026": 0.0,
            }

        venda = _safe_float(row.get("VENDA_LIQUIDA"))
        cresc = _safe_float(row.get("CRESCIMENTO_2026"))

        if ano == ano_atual:
            lojas[filial]["venda_ano_atual"]  += venda
            lojas[filial]["crescimento_2026"] += cresc
        elif ano == ano_anterior:
            lojas[filial]["venda_ano_anterior"] += venda

    resultado = []
    for item in sorted(lojas.values(), key=lambda x: x["venda_ano_atual"], reverse=True):
        ant = item["venda_ano_anterior"]
        atu = item["venda_ano_atual"]
        item["percentual_crescimento"] = (
            round((atu - ant) / ant * 100, 2) if ant != 0 else None
        )
        resultado.append(item)

    return {"status": "ok", "total": len(resultado), "data": resultado}


@router.get("/projecao-mensal")
async def projecao_mensal(
    ano:      Optional[int] = Query(default=None),
    mes:      Optional[str] = Query(default=None),
    filial:   Optional[str] = Query(default=None),
    grupo:    Optional[str] = Query(default=None),
    subgrupo: Optional[str] = Query(default=None),
    linha:    Optional[str] = Query(default=None),
    semestre: Optional[str] = Query(default=None),
    origem:   Optional[str] = Query(default=None),
    _key: str = Depends(get_api_key)
):
    dados = await _buscar_dados()
    if ano:
        dados = [r for r in dados if r.get("ANO") == ano]
    dados = _aplicar_filtros(dados, {
        "FILIAL": filial, "MES": mes, "GRUPO_PRODUTO": grupo,
        "SUBGRUPO_PRODUTO": subgrupo, "LINHA": linha,
        "SEMESTRE": semestre, "ORIGEM": origem,
    })
    return {"status": "ok", "total": len(dados), "data": dados}


@router.get("/por-grupo")
async def por_grupo(
    ano_atual:    int           = Query(default=2026),
    ano_anterior: int           = Query(default=2025),
    mes:          Optional[str] = Query(default=None),
    filial:       Optional[str] = Query(default=None),
    linha:        Optional[str] = Query(default=None),
    semestre:     Optional[str] = Query(default=None),
    _key: str = Depends(get_api_key)
):
    dados = await _buscar_dados()
    dados = _aplicar_filtros(dados, {
        "MES": mes, "FILIAL": filial,
        "LINHA": linha, "SEMESTRE": semestre,
    })

    grupos: dict[str, dict] = {}
    for row in dados:
        ano   = row.get("ANO")
        grupo = str(row.get("GRUPO_PRODUTO") or "").strip()
        if not grupo or ano not in (ano_atual, ano_anterior):
            continue

        if grupo not in grupos:
            grupos[grupo] = {
                "grupo_produto": grupo,
                "venda_ano_atual": 0.0,
                "venda_ano_anterior": 0.0,
                "qtde_ano_atual": 0,
                "crescimento_2026": 0.0,
            }

        venda = _safe_float(row.get("VENDA_LIQUIDA"))
        qtde  = int(row.get("QTDE") or 0)
        cresc = _safe_float(row.get("CRESCIMENTO_2026"))

        if ano == ano_atual:
            grupos[grupo]["venda_ano_atual"]  += venda
            grupos[grupo]["qtde_ano_atual"]   += qtde
            grupos[grupo]["crescimento_2026"] += cresc
        elif ano == ano_anterior:
            grupos[grupo]["venda_ano_anterior"] += venda

    resultado = []
    for item in sorted(grupos.values(), key=lambda x: x["venda_ano_atual"], reverse=True):
        ant = item["venda_ano_anterior"]
        atu = item["venda_ano_atual"]
        item["percentual_crescimento"] = (
            round((atu - ant) / ant * 100, 2) if ant != 0 else None
        )
        resultado.append(item)

    return {"status": "ok", "total": len(resultado), "data": resultado}


@router.get("/por-linha")
async def por_linha(
    ano_atual:    int           = Query(default=2026),
    ano_anterior: int           = Query(default=2025),
    mes:          Optional[str] = Query(default=None),
    filial:       Optional[str] = Query(default=None),
    grupo:        Optional[str] = Query(default=None),
    semestre:     Optional[str] = Query(default=None),
    _key: str = Depends(get_api_key)
):
    dados = await _buscar_dados()
    dados = _aplicar_filtros(dados, {
        "MES": mes, "FILIAL": filial,
        "GRUPO_PRODUTO": grupo, "SEMESTRE": semestre,
    })

    linhas: dict[str, dict] = {}
    for row in dados:
        ano   = row.get("ANO")
        linha = str(row.get("LINHA") or "").strip()
        if not linha or ano not in (ano_atual, ano_anterior):
            continue

        if linha not in linhas:
            linhas[linha] = {
                "linha": linha,
                "venda_ano_atual": 0.0,
                "venda_ano_anterior": 0.0,
                "qtde_ano_atual": 0,
            }

        venda = _safe_float(row.get("VENDA_LIQUIDA"))
        qtde  = int(row.get("QTDE") or 0)

        if ano == ano_atual:
            linhas[linha]["venda_ano_atual"] += venda
            linhas[linha]["qtde_ano_atual"]  += qtde
        elif ano == ano_anterior:
            linhas[linha]["venda_ano_anterior"] += venda

    resultado = sorted(linhas.values(), key=lambda x: x["venda_ano_atual"], reverse=True)
    return {"status": "ok", "total": len(resultado), "data": list(resultado)}


@router.get("/por-origem")
async def por_origem(
    ano_atual:    int           = Query(default=2026),
    ano_anterior: int           = Query(default=2025),
    mes:          Optional[str] = Query(default=None),
    filial:       Optional[str] = Query(default=None),
    semestre:     Optional[str] = Query(default=None),
    _key: str = Depends(get_api_key)
):
    dados = await _buscar_dados()
    dados = _aplicar_filtros(dados, {
        "MES": mes, "FILIAL": filial, "SEMESTRE": semestre,
    })

    origens: dict[str, dict] = {}
    for row in dados:
        ano    = row.get("ANO")
        origem = str(row.get("ORIGEM") or "").strip()
        if not origem or ano not in (ano_atual, ano_anterior):
            continue

        if origem not in origens:
            origens[origem] = {
                "origem": origem,
                "venda_ano_atual": 0.0,
                "venda_ano_anterior": 0.0,
            }

        venda = _safe_float(row.get("VENDA_LIQUIDA"))
        if ano == ano_atual:
            origens[origem]["venda_ano_atual"] += venda
        elif ano == ano_anterior:
            origens[origem]["venda_ano_anterior"] += venda

    return {"status": "ok", "total": len(origens), "data": list(origens.values())}