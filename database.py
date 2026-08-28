# =============================================================
# database.py — Conexão SQL Server via pyodbc
# =============================================================

import os
import pyodbc
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_connection():
    server   = os.getenv("DB_SERVER", "192.168.0.21")
    database = os.getenv("DB_NAME", "RCS_PAINEL")
    username = os.getenv("DB_USER", "ti_consulta")
    password = os.getenv("DB_PASSWORD", "consulta")
    driver   = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=30;"
    )
    try:
        return pyodbc.connect(conn_str)
    except Exception as e:
        logger.error(f"Erro ao conectar ao SQL Server: {e}")
        raise


def executar_procedure(nome: str) -> list[dict]:
    """Executa uma stored procedure e retorna lista de dicts."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SET NOCOUNT ON; SET LANGUAGE 'Portuguese'; EXEC {nome}")
        
        # Pula resultsets vazios até encontrar um com colunas
        while cursor.description is None:
            if not cursor.nextset():
                return []  # Nenhum resultado encontrado
        
        colunas = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(colunas, row)) for row in rows]
    except Exception as e:
        logger.error(f"Erro ao executar {nome}: {e}")
        raise
    finally:
        conn.close()

def executar_query(sql: str, params: tuple = ()) -> list[dict]:
    """Executa uma query SQL parametrizada e retorna lista de dicts."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        while cursor.description is None:
            if not cursor.nextset():
                return []
        colunas = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(colunas, row)) for row in rows]
    except Exception as e:
        logger.error(f"Erro na query: {e}")
        raise
    finally:
        conn.close()