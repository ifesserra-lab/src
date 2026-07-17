"""POC ETL — consulta ações do campus Serra no SRC/Ifes e salva 1 JSON por ação.

Fluxo (área pública, sem login):
  1. abre a consulta pública de ações
  2. seleciona o campus "Serra" e clica em Pesquisar
  3. percorre todas as páginas do resultado
  4. em cada linha clica no ícone "Detalhes" e captura o id da ação (iframe)
  5. baixa a página de detalhe de cada ação e salva um JSON individual

Extract  -> Playwright (lista) + httpx (detalhe server-side render)
Transform-> pares label/valor do panelGrid viram dict; datas/strings normalizadas
Load     -> data/serra/acao_<id>.json  (+ data/serra/_index.json)

Uso:
    pip install playwright httpx beautifulsoup4
    playwright install chromium
    python poc_serra.py

Env opcional:
    MAX_ACOES=5   # limita nº de ações (teste rápido). Vazio = todas.
"""

import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE = "https://src.ifes.edu.br/src/public/"
CONSULTA_URL = BASE + "consulta-acao.xhtml"
CAMPUS = "Serra"
OUT_DIR = Path(__file__).parent / "data" / "serra"

# ids PrimeFaces (estáveis para esta view)
DD_CAMPUS = "j_idt47:j_idt64"          # dropdown campus
BTN_PESQUISAR = "j_idt47:j_idt92"      # botão Pesquisar
TABELA = "j_idt47:dtblAcoes"           # dataTable de ações
MAX_ACOES = int(os.getenv("MAX_ACOES") or 0)  # 0 = todas


# ---------------------------------------------------------------- EXTRACT: lista
async def coletar_acoes() -> list[dict]:
    """Navega a UI e devolve [{acao_id, resumo_da_linha}] de todas as páginas."""
    coletados: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(CONSULTA_URL, wait_until="networkidle")

        # seleciona campus Serra (PrimeFaces selectonemenu)
        await page.locator(f"[id='{DD_CAMPUS}']").click()
        await page.wait_for_selector(f"[id='{DD_CAMPUS}_panel']")
        await page.locator(f"[id='{DD_CAMPUS}_panel'] li[data-label='{CAMPUS}']").click()
        await page.wait_for_selector(f"[id='{DD_CAMPUS}_panel']", state="hidden")

        # pesquisa — espera o AJAX repovoar a tabela (surge o 1º botão Detalhes)
        await page.locator(f"[id='{BTN_PESQUISAR}']").click()
        await page.wait_for_selector(
            f"[id='{TABELA}'] tbody tr button[title='Detalhes']", timeout=20000)

        # descobre total de páginas pelo paginador ("Página: 1/21")
        total_paginas = 1
        cur = await page.locator(f"[id='{TABELA}'] .ui-paginator-current").first.text_content()
        if cur:
            m = re.search(r"/(\d+)", cur)
            if m:
                total_paginas = int(m.group(1))
        print(f"[extract] {CAMPUS}: {total_paginas} páginas")

        for pag in range(1, total_paginas + 1):
            # botões "Detalhes" da página atual (title='Detalhes')
            botoes = page.locator(f"[id='{TABELA}'] tbody tr button[title='Detalhes']")
            n = await botoes.count()

            for i in range(n):
                botao = botoes.nth(i)
                bid = await botao.get_attribute("id")
                dlg = f"[id='{bid}_dlg']"

                # dados resumidos da linha (mesma linha do botão)
                linha = botao.locator("xpath=ancestor::tr[1]")
                resumo = [c.strip() for c in await linha.locator("td").all_text_contents()]

                # abre o dialog e lê o src do iframe (contém acao=<id>)
                await botao.click()
                await page.wait_for_selector(f"{dlg} iframe", state="attached", timeout=15000)
                src = await page.locator(f"{dlg} iframe").get_attribute("src")
                acao_id = parse_qs(urlparse(src).query).get("acao", [None])[0]

                coletados.append({"acao_id": acao_id, "linha": resumo, "src": urljoin(BASE, src)})

                # fecha o dialog e espera o overlay modal sumir antes do próximo clique
                await page.locator(f"{dlg} .ui-dialog-titlebar-close").click()
                await page.wait_for_selector(dlg, state="hidden", timeout=10000)
                await page.wait_for_selector(".ui-widget-overlay", state="hidden", timeout=10000)

                if MAX_ACOES and len(coletados) >= MAX_ACOES:
                    await browser.close()
                    print(f"[extract] limite MAX_ACOES={MAX_ACOES} atingido")
                    return coletados

            print(f"[extract] página {pag}/{total_paginas} -> {len(coletados)} ações")

            # próxima página
            if pag < total_paginas:
                nxt = page.locator(f"[id='{TABELA}'] .ui-paginator-next").first
                await nxt.click()
                await page.wait_for_timeout(1200)  # aguarda AJAX repovoar a tabela

        await browser.close()
    return coletados


# ------------------------------------------------------- EXTRACT+TRANSFORM: detalhe
def baixar_detalhe(client: httpx.Client, acao_id: str) -> dict:
    """GET na página de detalhe (render server-side) e devolve dict label->valor."""
    url = f"{BASE}detalha-acao.xhtml?acao={acao_id}"
    r = client.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # panelGrid: células alternam label, valor, label, valor...
    cells = [td.get_text(" ", strip=True) for td in soup.select("td.ui-panelgrid-cell")]
    dados: dict[str, str] = {}
    for i in range(0, len(cells) - 1, 2):
        chave, valor = cells[i], cells[i + 1]
        if chave:
            dados[chave] = valor
    return dados


# --------------------------------------------------------------------------- LOAD
def salvar_json(acao: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nome = f"acao_{acao['acao_id']}.json"
    caminho = OUT_DIR / nome
    caminho.write_text(json.dumps(acao, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    acoes = await coletar_acoes()
    print(f"[extract] total coletado: {len(acoes)} ações")

    index = []
    with httpx.Client(follow_redirects=True, headers={"User-Agent": "poc-etl-src-ifes/0.1"}) as client:
        for k, a in enumerate(acoes, 1):
            if not a["acao_id"]:
                print(f"  ! sem acao_id, pulando: {a['linha']}")
                continue
            try:
                detalhe = baixar_detalhe(client, a["acao_id"])
            except Exception as e:  # POC: loga e segue
                print(f"  ! erro detalhe acao={a['acao_id']}: {e}")
                continue

            registro = {
                "acao_id": a["acao_id"],
                "url_detalhe": a["src"],
                "campus": CAMPUS,
                **detalhe,
            }
            caminho = salvar_json(registro)
            index.append({"acao_id": a["acao_id"],
                          "processo": detalhe.get("Processo nº"),
                          "titulo": detalhe.get("Título ação"),
                          "arquivo": caminho.name})
            print(f"  [{k}/{len(acoes)}] salvo {caminho.name} — {detalhe.get('Título ação','')[:60]}")

    (OUT_DIR / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[load] {len(index)} JSONs em {OUT_DIR}")
    print(f"[load] índice: {OUT_DIR / '_index.json'}")


if __name__ == "__main__":
    asyncio.run(main())
