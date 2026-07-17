"""src_etl — ETL das ações públicas do SRC/Ifes com Playwright + httpx.

API principal:
    from src_etl import run, extrair_campus, Acao

    acoes = run("Serra", out_dir="data/serra")
"""

from __future__ import annotations

from .detail import fetch_detalhe, parse_detalhe
from .models import Acao
from .pipeline import (
    extrair_campi,
    extrair_campus,
    run,
    salvar_json_por_acao,
    salvar_por_campus,
)
from .scraper import LinhaAcao, coletar_campus, listar_campi

__version__ = "0.1.0"

__all__ = [
    "Acao",
    "LinhaAcao",
    "run",
    "extrair_campi",
    "extrair_campus",
    "salvar_json_por_acao",
    "salvar_por_campus",
    "coletar_campus",
    "listar_campi",
    "fetch_detalhe",
    "parse_detalhe",
    "__version__",
]
