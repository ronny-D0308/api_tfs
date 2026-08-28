"""
supabase_client.py — Camada de acesso a dados via Supabase.

Substitui a função executar_procedure() do database.py original.
Mantém o mesmo contrato de retorno (list[dict]) para que cache.py e
os routers não precisem de nenhuma outra alteração.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Cada cliente (empresa) que essa API atende. Se essa API um dia atender
# vários clientes ao mesmo tempo, isso vira um parâmetro por request
# em vez de uma constante fixa.
CLIENTE_ID = os.getenv("CLIENTE_ID", "tfseven")

# As tabelas no Supabase usam colunas em minúsculo (snake_case).
# Os routers (vendas.py, filtros.py) foram escritos esperando os nomes
# ORIGINAIS do SQL Server (MAIÚSCULO). Por isso, ao ler do Supabase,
# convertemos de volta — assim os routers não precisam de nenhuma alteração.
_MAPAS_REVERSOS = {
    "vendas": {
        "tipo_filial": "TIPO_FILIAL",
        "codigo_filial": "CODIGO_FILIAL",
        "filial": "FILIAL",
        "origem": "ORIGEM",
        "tipo": "TIPO",
        "cliente_varejo": "CLIENTE_VAREJO",
        "data_venda": "DATA_VENDA",
        "ano": "ANO",
        "mes": "MES",
        "semestre": "SEMESTRE",
        "produto": "PRODUTO",
        "desc_produto": "DESC_PRODUTO",
        "grupo_produto": "GRUPO_PRODUTO",
        "subgrupo_produto": "SUBGRUPO_PRODUTO",
        "linha": "LINHA",
        "qtde": "QTDE",
        "venda_liquida": "VENDA_LIQUIDA",
        "pct_cresc": "% Cresc",
        "crescimento_2026": "CRESCIMENTO_2026",
    },
    "filiais_ref": {
        "codigo_filial": "CODIGO_FILIAL",
        "filial": "FILIAL",
        "canal": "CANAL",
    },
    "produtos_ref": {
        "produto": "PRODUTO",
        "desc_produto": "DESC_PRODUTO",
        "grupo_produto": "GRUPO_PRODUTO",
        "subgrupo_produto": "SUBGRUPO_PRODUTO",
        "linha": "LINHA",
    },
}


def _converter_para_formato_original(registro: dict, tabela: str) -> dict:
    mapa = _MAPAS_REVERSOS.get(tabela)
    if not mapa:
        return registro
    return {mapa.get(k, k): v for k, v in registro.items() if k not in ("id", "cliente_id", "sincronizado_em")}


def executar_procedure(tabela: str = "vendas", cliente_id: str = None) -> list[dict]:
    """
    Busca todos os registros da tabela no Supabase para o cliente configurado.
    Usa paginação automática, pois o PostgREST limita ~1000 linhas por requisição.
    """
    cliente_id = cliente_id or CLIENTE_ID

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }

    url = f"{SUPABASE_URL}/rest/v1/{tabela}"
    params = {
        "cliente_id": f"eq.{cliente_id}",
        "select": "*",
    }

    todos_registros = []
    offset = 0
    tamanho_pagina = 1000

    while True:
        headers_paginacao = {
            **headers,
            "Range-Unit": "items",
            "Range": f"{offset}-{offset + tamanho_pagina - 1}",
        }
        resp = requests.get(url, headers=headers_paginacao, params=params, timeout=30)
        resp.raise_for_status()

        pagina = resp.json()
        pagina_convertida = [_converter_para_formato_original(r, tabela) for r in pagina]
        todos_registros.extend(pagina_convertida)

        if len(pagina) < tamanho_pagina:
            break  # última página
        offset += tamanho_pagina

    return todos_registros


def executar_query(tabela_ou_sql: str, params=None) -> list[dict]:
    """
    Adaptador de compatibilidade com cache.py's get_filiais()/get_produtos(),
    que chamam a função como executar_query_fn(sql, params).

    Nesta versão cloud, não existe SQL arbitrário: 'tabela_ou_sql' é, na
    prática, o NOME da tabela de referência já sincronizada no Supabase
    (filiais_ref, produtos_ref) — o parâmetro 'params' é ignorado.
    """
    return executar_procedure(tabela=tabela_ou_sql)