"""Camada de dashboard: agregações e geração do site estático (HTML).

Módulos:
    relatorio       — agregações-base + gráficos SVG + relatório "visão geral"
    indicadores     — indicadores avançados (alunos únicos, recorrência, ...)
    rede            — programas guarda-chuva + rede de colaboração
    formados        — cruzamento formados × extensão
    extensionistas  — coleta de extensionistas + resumos IA (Mistral)
    painel          — design system (DESIGN.md) + shell + painel de abas
    site            — mini-site multi-página (ações, atividades, busca, listas)
"""

from .extensionistas import coletar_extensionistas, gerar_resumos
from .indicadores import gerar_indicadores
from .painel import gerar_painel, montar_shell
from .relatorio import agregar, gerar_relatorio
from .site import gerar_site

__all__ = [
    "gerar_relatorio", "gerar_indicadores", "gerar_painel", "gerar_site",
    "agregar", "montar_shell", "coletar_extensionistas", "gerar_resumos",
]
