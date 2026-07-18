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


async def _selecionar_e_pesquisar(page, campus: str) -> int:
    """Abre a consulta, seleciona o campus, pesquisa e devolve o total de páginas."""
    await page.goto(CONSULTA_URL, wait_until="networkidle")
    await page.locator(f"[id='{_DD_CAMPUS}']").click()
    await page.wait_for_selector(f"[id='{_DD_CAMPUS}_panel']")
    await page.locator(f"[id='{_DD_CAMPUS}_panel'] li[data-label='{campus}']").click()
    await page.wait_for_selector(f"[id='{_DD_CAMPUS}_panel']", state="hidden")
    await page.locator(f"[id='{_BTN_PESQUISAR}']").click()
    await page.wait_for_selector(
        f"[id='{_TABELA}'] tbody tr button[title='Detalhes']", timeout=20000)
    total = 1
    cur = await page.locator(f"[id='{_TABELA}'] .ui-paginator-current").first.text_content()
    if cur and (m := re.search(r"/(\d+)", cur)):
        total = int(m.group(1))
    return total


async def _scrape_pagina(page, log) -> list[LinhaAcao]:
    """Extrai as ações da página atual (clica cada dialog Detalhes)."""
    await page.wait_for_selector(
        f"[id='{_TABELA}'] tbody tr button[title='Detalhes']", timeout=20000)
    ids = await page.eval_on_selector_all(
        f"[id='{_TABELA}'] tbody tr button[title='Detalhes']", "els=>els.map(e=>e.id)")
    out: list[LinhaAcao] = []
    for bid in ids:
        dlg = f"[id='{bid}_dlg']"
        try:
            botao = page.locator(f"[id='{bid}']")
            linha = botao.locator("xpath=ancestor::tr[1]")
            resumo = [c.strip() for c in await linha.locator("td").all_text_contents()]
            await botao.click()
            await page.wait_for_selector(f"{dlg} iframe", state="attached", timeout=15000)
            src = await page.locator(f"{dlg} iframe").get_attribute("src")
            acao_id = parse_qs(urlparse(src).query).get("acao", [None])[0]
            out.append(LinhaAcao(acao_id=acao_id, url_detalhe=urljoin(BASE, src), linha=resumo))
            await page.locator(f"{dlg} .ui-dialog-titlebar-close").click()
            await page.wait_for_selector(dlg, state="hidden", timeout=10000)
            await page.wait_for_selector(".ui-widget-overlay", state="hidden", timeout=10000)
        except Exception as e:  # uma linha ruim não derruba o crawl
            log(f"  ! falha na linha {bid}: {str(e)[:80]}")
            try:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(400)
            except Exception:
                pass
    return out


async def _proxima_pagina(page) -> None:
    await page.locator(f"[id='{_TABELA}'] .ui-paginator-next").first.click()
    await page.wait_for_timeout(1200)


async def _worker(browser, campus: str, quais: set[int], wid: int, log) -> list[LinhaAcao]:
    """Um worker: percorre todas as páginas, mas só raspa as suas (round-robin)."""
    ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await ctx.new_page()
    total = await _selecionar_e_pesquisar(page, campus)
    coletados: list[LinhaAcao] = []
    for pag in range(1, total + 1):
        if pag in quais:
            linhas = await _scrape_pagina(page, log)
            coletados.extend(linhas)
            log(f"[w{wid}] página {pag}/{total} -> +{len(linhas)}")
        if pag < total:
            await _proxima_pagina(page)
    await ctx.close()
    return coletados


async def coletar_campus(
    campus: str,
    *,
    headless: bool = True,
    max_acoes: int | None = None,
    on_progress=None,
    workers: int = 1,
) -> list[LinhaAcao]:
    """Percorre a consulta pública e devolve as ações de um campus.

    Args:
        campus: nome exato do campus (ex.: "Serra").
        headless: roda o navegador sem interface.
        max_acoes: limite opcional de ações (só no modo serial, para testes).
        on_progress: callback(msg:str) para logs de progresso.
        workers: nº de abas paralelas (público, sem login). >1 divide as páginas
                 em round-robin entre workers e ignora max_acoes.
    """
    log = on_progress or (lambda _m: None)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)

        # descobre o total de páginas
        page0 = await browser.new_page(viewport={"width": 1440, "height": 900})
        total = await _selecionar_e_pesquisar(page0, campus)
        log(f"{campus}: {total} páginas" + (f" | {workers} workers" if workers > 1 else ""))

        if workers <= 1:
            coletados: list[LinhaAcao] = []
            for pag in range(1, total + 1):
                coletados.extend(await _scrape_pagina(page0, log))
                log(f"página {pag}/{total} -> {len(coletados)} ações")
                if max_acoes and len(coletados) >= max_acoes:
                    await browser.close()
                    log(f"limite max_acoes={max_acoes} atingido")
                    return coletados[:max_acoes]
                if pag < total:
                    await _proxima_pagina(page0)
            await browser.close()
            return coletados

        # paralelo: cada worker cuida de páginas pag onde (pag-1) % workers == w
        await page0.close()
        import asyncio
        k = min(workers, total)
        tarefas = [
            _worker(browser, campus, {pag for pag in range(1, total + 1) if (pag - 1) % k == w},
                    w, log)
            for w in range(k)
        ]
        partes = await asyncio.gather(*tarefas)
        await browser.close()
        return [linha for parte in partes for linha in parte]
