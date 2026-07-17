"""Extração + parse da página de detalhe de uma ação (render server-side).

A página `detalha-acao.xhtml?acao=<id>` é renderizada no servidor (JSF), então
basta um GET simples com httpx — não precisa de navegador.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

BASE = "https://src.ifes.edu.br/src/public/"
USER_AGENT = "src-etl/0.1 (+https://github.com/ifesserra-lab/SRC_ETL)"


def detalhe_url(acao_id: str) -> str:
    return f"{BASE}detalha-acao.xhtml?acao={acao_id}"


def parse_detalhe(html: str) -> dict[str, str]:
    """Converte o panelGrid (células alternando rótulo/valor) em dict."""
    soup = BeautifulSoup(html, "html.parser")
    cells = [td.get_text(" ", strip=True) for td in soup.select("td.ui-panelgrid-cell")]
    dados: dict[str, str] = {}
    for i in range(0, len(cells) - 1, 2):
        chave, valor = cells[i], cells[i + 1]
        if chave:
            dados[chave] = valor
    return dados


def fetch_detalhe(acao_id: str, client: httpx.Client | None = None) -> dict[str, str]:
    """Baixa e parseia a página de detalhe de uma ação."""
    own = client is None
    client = client or httpx.Client(
        follow_redirects=True, headers={"User-Agent": USER_AGENT}, timeout=30
    )
    try:
        r = client.get(detalhe_url(acao_id))
        r.raise_for_status()
        return parse_detalhe(r.text)
    finally:
        if own:
            client.close()
