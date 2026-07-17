"""Navegação da consulta pública de ações (Playwright).

Seleciona um campus, pesquisa e percorre todas as páginas do resultado,
capturando o id de cada ação (via iframe do dialog "Detalhes").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.async_api import async_playwright

CONSULTA_URL = "https://src.ifes.edu.br/src/public/consulta-acao.xhtml"
BASE = "https://src.ifes.edu.br/src/public/"

# ids PrimeFaces estáveis desta view
_DD_CAMPUS = "j_idt47:j_idt64"
_BTN_PESQUISAR = "j_idt47:j_idt92"
_TABELA = "j_idt47:dtblAcoes"


@dataclass
class LinhaAcao:
    """Referência a uma ação encontrada na listagem."""

    acao_id: str | None
    url_detalhe: str | None
    linha: list[str] = field(default_factory=list)


async def listar_campi(*, headless: bool = True) -> list[str]:
    """Lê os campi disponíveis no dropdown da consulta (sem 'Selecione')."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(CONSULTA_URL, wait_until="networkidle")
        opts = await page.eval_on_selector_all(
            f"[id='{_DD_CAMPUS}_input'] option",
            "els => els.map(e => e.textContent.trim())",
        )
        await browser.close()
    return [o for o in opts if o and o.lower() != "selecione"]


async def coletar_campus(
    campus: str,
    *,
    headless: bool = True,
    max_acoes: int | None = None,
    on_progress=None,
) -> list[LinhaAcao]:
    """Percorre a consulta pública e devolve as ações de um campus.

    Args:
        campus: nome exato do campus (ex.: "Serra").
        headless: roda o navegador sem interface.
        max_acoes: limite opcional de ações (para testes).
        on_progress: callback(msg:str) para logs de progresso.
    """
    log = on_progress or (lambda _m: None)
    coletados: list[LinhaAcao] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(CONSULTA_URL, wait_until="networkidle")

        # seleciona o campus (PrimeFaces selectonemenu)
        await page.locator(f"[id='{_DD_CAMPUS}']").click()
        await page.wait_for_selector(f"[id='{_DD_CAMPUS}_panel']")
        await page.locator(f"[id='{_DD_CAMPUS}_panel'] li[data-label='{campus}']").click()
        await page.wait_for_selector(f"[id='{_DD_CAMPUS}_panel']", state="hidden")

        # pesquisa e aguarda o AJAX repovoar a tabela
        await page.locator(f"[id='{_BTN_PESQUISAR}']").click()
        await page.wait_for_selector(
            f"[id='{_TABELA}'] tbody tr button[title='Detalhes']", timeout=20000
        )

        # total de páginas ("Página: 1/21")
        total_paginas = 1
        cur = await page.locator(f"[id='{_TABELA}'] .ui-paginator-current").first.text_content()
        if cur and (m := re.search(r"/(\d+)", cur)):
            total_paginas = int(m.group(1))
        log(f"{campus}: {total_paginas} páginas")

        for pag in range(1, total_paginas + 1):
            botoes = page.locator(f"[id='{_TABELA}'] tbody tr button[title='Detalhes']")
            n = await botoes.count()

            for i in range(n):
                botao = botoes.nth(i)
                bid = await botao.get_attribute("id")
                dlg = f"[id='{bid}_dlg']"

                linha = botao.locator("xpath=ancestor::tr[1]")
                resumo = [c.strip() for c in await linha.locator("td").all_text_contents()]

                await botao.click()
                await page.wait_for_selector(f"{dlg} iframe", state="attached", timeout=15000)
                src = await page.locator(f"{dlg} iframe").get_attribute("src")
                acao_id = parse_qs(urlparse(src).query).get("acao", [None])[0]

                coletados.append(
                    LinhaAcao(acao_id=acao_id, url_detalhe=urljoin(BASE, src), linha=resumo)
                )

                # fecha dialog e espera overlay sumir
                await page.locator(f"{dlg} .ui-dialog-titlebar-close").click()
                await page.wait_for_selector(dlg, state="hidden", timeout=10000)
                await page.wait_for_selector(".ui-widget-overlay", state="hidden", timeout=10000)

                if max_acoes and len(coletados) >= max_acoes:
                    await browser.close()
                    log(f"limite max_acoes={max_acoes} atingido")
                    return coletados

            log(f"página {pag}/{total_paginas} -> {len(coletados)} ações")

            if pag < total_paginas:
                await page.locator(f"[id='{_TABELA}'] .ui-paginator-next").first.click()
                await page.wait_for_timeout(1200)

        await browser.close()
    return coletados
