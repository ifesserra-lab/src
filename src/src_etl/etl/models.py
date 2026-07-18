"""Modelos de dados (schema) das ações extraídas do SRC/Ifes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Acao(BaseModel):
    """Uma ação (projeto/curso/evento...) registrada no SRC.

    Os campos seguem os rótulos da página de detalhe. Campos ausentes na
    página ficam como string vazia / None.
    """

    acao_id: str = Field(..., description="Identificador interno da ação no SRC")
    url_detalhe: str | None = None
    campus: str | None = None

    processo: str | None = Field(None, alias="Processo nº")
    natureza: str | None = Field(None, alias="Natureza")
    coordenador: str | None = Field(None, alias="Coordenador(a)")
    tipo: str | None = Field(None, alias="Tipo ação")
    titulo: str | None = Field(None, alias="Título ação")
    fomento: str | None = Field(None, alias="Fomento")
    acao_vinculante: str | None = Field(None, alias="Ação vinculante")
    grande_area: str | None = Field(None, alias="Grande área conhecimento")
    area_tematica_principal: str | None = Field(None, alias="Área temática principal")
    area_tematica_secundaria: str | None = Field(None, alias="Área temática secundária")
    relatorio_aprovado: str | None = Field(None, alias="Relatório aprovado")
    data_ultimo_relatorio: str | None = Field(None, alias="Data último relatório")
    data_cadastro: str | None = Field(None, alias="Data de cadastro")
    resumo: str | None = Field(None, alias="Resumo")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @classmethod
    def from_labels(cls, acao_id: str, campos: dict[str, str], **extra) -> "Acao":
        """Cria a partir do dict rótulo->valor extraído do panelGrid."""
        return cls(acao_id=acao_id, **{**campos, **extra})


class AtividadeParticipacoes(BaseModel):
    """Uma atividade da ação, com público-alvo (alunos atendidos) e equipe.

    Cada pessoa é um dict rótulo->valor (colunas da tabela), preservando os
    campos como aparecem no sistema (Nome, CPF, E-mail, Situação, ...).
    """

    num: str | None = None
    atividade: str | None = None
    atividade_id: str | None = None
    tipo: str | None = None
    publico_alvo: list[dict[str, str]] = Field(default_factory=list)
    equipe_execucao: list[dict[str, str]] = Field(default_factory=list)


class AcaoParticipacoes(BaseModel):
    """Participações de uma ação (por processo), agregando suas atividades."""

    processo: str
    total_atividades: int = 0
    total_publico_alvo: int = 0
    total_equipe: int = 0
    atividades: list[AtividadeParticipacoes] = Field(default_factory=list)
