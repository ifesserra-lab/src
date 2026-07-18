"""src_etl — ETL das ações públicas do SRC/Ifes com Playwright + httpx.

API principal:
    from src_etl import run, extrair_campus, Acao

    acoes = run("Serra", out_dir="data/serra")
"""

from __future__ import annotations

from .detail import fetch_detalhe, parse_detalhe
from .gerenciar import carregar_credenciais, coletar_participacoes
from .models import Acao, AcaoParticipacoes, AtividadeParticipacoes
from .pipeline import (
    extrair_campi,
    extrair_campus,
    processos_de_index,
    run,
    run_participacoes,
    salvar_json_por_acao,
    salvar_por_campus,
)
from .consolidar import consolidar
from .enriquecer import enriquecer_acoes
from .indicadores import gerar_indicadores
from .relatorio import gerar_relatorio
from .scraper import LinhaAcao, coletar_campus, listar_campi

__version__ = "0.9.0"

__all__ = [
    "Acao",
    "AcaoParticipacoes",
    "AtividadeParticipacoes",
    "LinhaAcao",
    "run",
    "run_participacoes",
    "processos_de_index",
    "extrair_campi",
    "extrair_campus",
    "salvar_json_por_acao",
    "salvar_por_campus",
    "coletar_campus",
    "listar_campi",
    "coletar_participacoes",
    "carregar_credenciais",
    "gerar_relatorio",
    "enriquecer_acoes",
    "consolidar",
    "gerar_indicadores",
    "fetch_detalhe",
    "parse_detalhe",
    "__version__",
]
