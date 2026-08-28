"""
supabase_client.py — Camada de acesso a dados via Supabase.

Substitui a função executar_procedure() do database.py original.
Mantém o mesmo contrato de retorno (list[dict]) para que cache.py e
os routers não precisem de nenhuma outra alteração.
"""

import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    Primeiro descobre o total de linhas (via header Content-Range) e depois
    busca todas as páginas EM PARALELO, em vez de uma por vez — isso reduz
    drasticamente o tempo total para tabelas grandes (ex: 228k linhas).
    """
    cliente_id = cliente_id or CLIENTE_ID
    tamanho_pagina = 1000
    max_workers = 10  # nº de requisições simultâneas ao Supabase

    headers_base = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    url = f"{SUPABASE_URL}/rest/v1/{tabela}"
    params = {
        "cliente_id": f"eq.{cliente_id}",
        "select": "*",
    }

    def buscar_pagina(offset: int, pedir_total: bool = False):
        headers = {
            **headers_base,
            "Range-Unit": "items",
            "Range": f"{offset}-{offset + tamanho_pagina - 1}",
        }
        if pedir_total:
            headers["Prefer"] = "count=exact"
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return offset, resp.json(), resp.headers.get("Content-Range")

    # --- 1ª página: pede o total exato via "Prefer: count=exact" ---
    primeiro_offset, primeira_pagina, content_range = buscar_pagina(0, pedir_total=True)
    todos_registros = list(primeira_pagina)

    total = None
    if content_range and "/" in content_range:
        try:
            total = int(content_range.split("/")[-1])
        except ValueError:
            total = None  # veio "*" — total desconhecido

    # Primeira página já veio incompleta: é a última mesmo, não precisa de mais nada.
    if len(primeira_pagina) < tamanho_pagina:
        return [_converter_para_formato_original(r, tabela) for r in todos_registros]

    # Caso o total não venha (situação inesperada), cai para paginação sequencial seguro,
    # em vez de arriscar retornar dados incompletos silenciosamente.
    if total is None:
        offset = tamanho_pagina
        while True:
            _, pagina, _ = buscar_pagina(offset)
            todos_registros.extend(pagina)
            if len(pagina) < tamanho_pagina:
                break
            offset += tamanho_pagina
        return [_converter_para_formato_original(r, tabela) for r in todos_registros]

    # --- Páginas restantes, em paralelo ---
    offsets_restantes = list(range(tamanho_pagina, total, tamanho_pagina))
    resultados_por_offset = {}

    if offsets_restantes:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futuros = {executor.submit(buscar_pagina, off): off for off in offsets_restantes}
            for futuro in as_completed(futuros):
                offset, pagina, _ = futuro.result()
                resultados_por_offset[offset] = pagina

    for offset in offsets_restantes:
        todos_registros.extend(resultados_por_offset.get(offset, []))

    return [_converter_para_formato_original(r, tabela) for r in todos_registros]


def executar_query(tabela_ou_sql: str, params=None) -> list[dict]:
    """
    Adaptador de compatibilidade com cache.py's get_filiais()/get_produtos(),
    que chamam a função como executar_query_fn(sql, params).

    Nesta versão cloud, não existe SQL arbitrário: 'tabela_ou_sql' é, na
    prática, o NOME da tabela de referência já sincronizada no Supabase
    (filiais_ref, produtos_ref) — o parâmetro 'params' é ignorado.
    """
    return executar_procedure(tabela=tabela_ou_sql)