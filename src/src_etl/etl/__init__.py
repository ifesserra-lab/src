"""Camada de ETL: extração (SRC público + autenticado), transformação e carga.

Módulos:
    models      — schemas pydantic (Acao, AcaoParticipacoes, ...)
    scraper     — consulta pública de ações (Playwright)
    detail      — página de detalhe da ação (httpx, sem browser)
    gerenciar   — participações via área autenticada (público-alvo + equipe)
    vinculadas  — vínculos programa -> ações filhas (fonte oficial)
    enriquecer  — completa categorias vazias via Mistral (não-destrutivo)
    consolidar  — une ações + participações num único JSON
    pipeline    — orquestração e pontos de entrada síncronos
"""

from .consolidar import consolidar
from .detail import fetch_detalhe, parse_detalhe
from .enriquecer import enriquecer_acoes
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
from .scraper import LinhaAcao, coletar_campus, listar_campi
from .vinculadas import enriquecer_vinculadas

__all__ = [
    "Acao", "AcaoParticipacoes", "AtividadeParticipacoes", "LinhaAcao",
    "run", "run_participacoes", "processos_de_index",
    "extrair_campi", "extrair_campus",
    "salvar_json_por_acao", "salvar_por_campus",
    "coletar_campus", "listar_campi",
    "coletar_participacoes", "carregar_credenciais",
    "fetch_detalhe", "parse_detalhe",
    "enriquecer_acoes", "enriquecer_vinculadas", "consolidar",
]
