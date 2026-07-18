"""src_etl — ETL e dashboard das ações do SRC/Ifes.

Organização:
    src_etl.etl        — extração (pública + autenticada), enriquecimento,
                         consolidação e pipeline
    src_etl.dashboard  — agregações, painel e mini-site estático

A API pública é re-exportada aqui para conveniência e compatibilidade:

    from src_etl import run, run_participacoes, gerar_painel, gerar_site
"""

from __future__ import annotations

from .dashboard import (
    coletar_extensionistas,
    gerar_indicadores,
    gerar_painel,
    gerar_relatorio,
    gerar_resumos,
    gerar_site,
)
from .etl import (
    Acao,
    AcaoParticipacoes,
    AtividadeParticipacoes,
    LinhaAcao,
    carregar_credenciais,
    coletar_campus,
    coletar_participacoes,
    consolidar,
    enriquecer_acoes,
    enriquecer_vinculadas,
    extrair_campi,
    extrair_campus,
    fetch_detalhe,
    listar_campi,
    parse_detalhe,
    processos_de_index,
    run,
    run_participacoes,
    salvar_json_por_acao,
    salvar_por_campus,
)

__version__ = "0.29.0"

__all__ = [
    # etl
    "Acao", "AcaoParticipacoes", "AtividadeParticipacoes", "LinhaAcao",
    "run", "run_participacoes", "processos_de_index",
    "extrair_campi", "extrair_campus",
    "salvar_json_por_acao", "salvar_por_campus",
    "coletar_campus", "listar_campi",
    "coletar_participacoes", "carregar_credenciais",
    "fetch_detalhe", "parse_detalhe",
    "enriquecer_acoes", "enriquecer_vinculadas", "consolidar",
    # dashboard
    "gerar_relatorio", "gerar_indicadores", "gerar_painel", "gerar_site",
    "coletar_extensionistas", "gerar_resumos",
    "__version__",
]
