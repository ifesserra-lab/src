"""Fluxo autenticado: Gerenciar > Ações > pesquisa por processo.

Para cada atividade da ação coleta:
  - Público-Alvo   (alunos atendidos)   -> gerenciar-publico-alvo.xhtml?atividade=<id>
  - Equipe Execução (equipe executora)  -> gerenciar-equipe-execucao.xhtml?atividade=<id>

Exige login (credenciais em .env: USER / PASSWORD). O site mantém UMA sessão
por usuário, então o fluxo é sequencial e reusa a mesma sessão.

ATENÇÃO: coleta dados pessoais (nome, CPF, e-mail). Mantenha o resultado local;
`data/` já está no .gitignore.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import Page, async_playwright

from .models import AcaoParticipacoes, AtividadeParticipacoes

LOGIN_URL = "https://src.ifes.edu.br/src"
GER_ACAO = "https://src.ifes.edu.br/src/pages/gerenciar/gerenciar-acao.xhtml"
PUBLICO = "https://src.ifes.edu.br/src/pages/gerenciar/gerenciar-publico-alvo.xhtml?atividade="
EQUIPE = "https://src.ifes.edu.br/src/pages/gerenciar/gerenciar-equipe-execucao.xhtml?atividade="
_TBL = "frmMain:dtblParticipacoes"


# ------------------------------------------------------------------ credenciais
def carregar_credenciais(env_path: str | Path = ".env") -> tuple[str, str]:
    """Lê credenciais do arquivo .env (USER/PASSWORD) com fallback a SRC_USER/SRC_PASS.

    O arquivo .env tem precedência: no SO, `USER` já é uma variável de ambiente
    (nome do usuário do sistema) e sombrearia o valor pretendido.
    """
    arquivo: dict[str, str] = {}
    p = Path(env_path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                arquivo[k.strip()] = v.strip()

    def pega(*chaves: str) -> str | None:
        for k in chaves:            # 1) arquivo .env (autoritativo)
            if arquivo.get(k):
                return arquivo[k]
        for k in chaves:            # 2) ambiente, só chaves inequívocas SRC_*
            if k.startswith("SRC_") and os.environ.get(k):
                return os.environ[k]
        return None

    user = pega("USER", "SRC_USER")
    senha = pega("PASSWORD", "SRC_PASS")
    if not user or not senha:
        raise RuntimeError("Credenciais ausentes: defina USER e PASSWORD no .env")
    return user, senha


# ------------------------------------------------------------------ navegação
async def _logado(page: Page) -> bool:
    """True se autenticado (não está na tela de login)."""
    return await page.eval_on_selector_all("input[placeholder='Senha']", "e=>e.length") == 0


async def _login(page: Page, user: str, senha: str) -> None:
    for _ in range(3):
        await page.goto(LOGIN_URL, wait_until="networkidle")
        if await _logado(page):  # sessão ainda válida
            return
        await page.fill("input[placeholder='Usuário']", user)
        await page.fill("input[placeholder='Senha']", senha)
        await page.click("button:has-text('Entrar')")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)
        if await _logado(page):
            return
    raise RuntimeError("falha no login (verifique USER/PASSWORD)")


async def _ir_busca(page: Page) -> bool:
    """Vai ao form de busca de ação (retry tolerante a estado transitório)."""
    for _ in range(5):
        await page.goto(GER_ACAO, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        if await page.eval_on_selector_all("input.ui-inputmask", "e=>e.length"):
            return True
        await page.wait_for_timeout(2000)
    return False


async def _pesquisar(page: Page, processo: str) -> None:
    """Preenche o campo mascarado (dígitos) e clica Pesquisar, com verificação."""
    digitos = "".join(c for c in processo if c.isdigit())
    campo = page.locator("input.ui-inputmask")
    for _ in range(4):
        await campo.click()
        await page.wait_for_timeout(250)
        await campo.press("Control+A")
        await campo.press("Delete")
        await page.wait_for_timeout(150)
        await campo.type(digitos, delay=80)
        if "".join(c for c in await campo.input_value() if c.isdigit()) == digitos:
            break
    await page.click("button[title='Pesquisar']")
    await page.wait_for_timeout(3500)


async def _atividades(page: Page) -> list[dict[str, str]]:
    """Lê a tabela de atividades (dtblAtividades) da ação pesquisada."""
    return await page.evaluate(
        """() => [...document.querySelectorAll("[id$='dtblAtividades'] tbody tr")].map(tr => {
            const c=[...tr.querySelectorAll('td')].map(td=>td.innerText.trim());
            return {num:c[0]||'', tipo:c[1]||'', atividade:c[2]||''};
        }).filter(r => r.num && r.num.toLowerCase().indexOf('nenhum')<0)"""
    )


async def _scrape_participacoes(page: Page) -> list[dict[str, str]]:
    """Lê a tabela dtblParticipacoes em TODAS as páginas -> lista de dicts."""
    await page.wait_for_selector(f"[id='{_TBL}']", timeout=15000)
    headers = await page.eval_on_selector_all(
        f"[id='{_TBL}'] thead th", "els=>els.map(e=>e.innerText.trim())"
    )
    manter = [i for i, h in enumerate(headers) if h and h.lower() != "operação"]

    linhas: list[dict[str, str]] = []
    while True:
        rows = await page.evaluate(
            f"""() => [...document.querySelectorAll("[id='{_TBL}'] tbody tr")]
                    .map(tr => [...tr.querySelectorAll('td')].map(td=>td.innerText.trim()))"""
        )
        for r in rows:
            if len(r) <= 1 or (r and "nenhum" in r[0].lower()):
                continue
            linhas.append({headers[i]: (r[i] if i < len(r) else "") for i in manter})

        nxt = page.locator(f"[id='{_TBL}'] .ui-paginator-next").first
        if await nxt.count() == 0:
            break
        cls = await nxt.get_attribute("class") or ""
        if "ui-state-disabled" in cls:
            break
        await nxt.click()
        await page.wait_for_timeout(1000)
    return linhas


async def _coletar_processo(page: Page, processo: str, log) -> AcaoParticipacoes:
    """Coleta público-alvo + equipe de todas as atividades de um processo."""
    if not await _ir_busca(page):
        raise RuntimeError("não chegou ao form de busca (sessão)")
    await _pesquisar(page, processo)
    metas = await _atividades(page)
    log(f"[{processo}] {len(metas)} atividades")

    ativs: list[AtividadeParticipacoes] = []
    for i, meta in enumerate(metas):
        if i > 0:  # re-pesquisa: cada clique navega pra fora da lista
            await _ir_busca(page)
            await _pesquisar(page, processo)

        botoes = page.locator("button[title='Público-Alvo']")
        if await botoes.count() <= i:
            break
        await botoes.nth(i).click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)
        atividade_id = page.url.split("atividade=")[-1]
        publico = await _scrape_participacoes(page)

        # equipe via deep-link pelo mesmo atividade_id
        await page.goto(EQUIPE + quote(atividade_id, safe=""), wait_until="networkidle")
        await page.wait_for_timeout(1200)
        equipe = await _scrape_participacoes(page)

        ativs.append(AtividadeParticipacoes(
            num=meta["num"], atividade=meta["atividade"], tipo=meta["tipo"],
            atividade_id=atividade_id, publico_alvo=publico, equipe_execucao=equipe,
        ))
        log(f"  ativ {meta['num']} (id={atividade_id}): "
            f"público={len(publico)} equipe={len(equipe)}")

    return AcaoParticipacoes(
        processo=processo,
        total_atividades=len(ativs),
        total_publico_alvo=sum(len(a.publico_alvo) for a in ativs),
        total_equipe=sum(len(a.equipe_execucao) for a in ativs),
        atividades=ativs,
    )


async def _processar_lista(page: Page, processos: list[str],
                           log, on_processo, retry: int = 2) -> dict[str, AcaoParticipacoes]:
    """Processa uma fatia de processos numa aba (com retry por processo)."""
    res: dict[str, AcaoParticipacoes] = {}
    for proc in processos:
        for tent in range(retry):
            try:
                ap = await _coletar_processo(page, proc, log)
                res[proc] = ap
                if on_processo:
                    on_processo(ap)  # salva já, protege progresso
                break
            except Exception as e:
                if tent + 1 >= retry:
                    log(f"[{proc}] ERRO (após {retry} tentativas): {str(e)[:70]}")
                else:
                    await page.wait_for_timeout(1500)
    return res


async def coletar_participacoes(
    processos: list[str],
    *,
    user: str | None = None,
    senha: str | None = None,
    headless: bool = True,
    on_progress=None,
    on_processo=None,
    workers: int = 1,
) -> dict[str, AcaoParticipacoes]:
    """UM login; coleta participações de vários processos.

    workers>1 abre N abas na MESMA sessão (um único login) e divide os processos
    entre elas — validado: o estado por-aba do JSF não é clobberado. Cada aba
    roda sua fatia sequencialmente; as abas rodam concorrentes.

    on_processo(AcaoParticipacoes): callback ao concluir cada processo (save
    incremental — seguro entre abas, pois o event loop é cooperativo).
    """
    log = on_progress or (lambda _m: None)
    if not user or not senha:
        user, senha = carregar_credenciais()

    resultado: dict[str, AcaoParticipacoes] = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})

        # LOGIN uma única vez (cookie compartilhado por todas as abas do contexto)
        login_page = await ctx.new_page()
        await _login(login_page, user, senha)
        log(f"login OK ({len(processos)} processos, {max(1, workers)} aba(s))")

        k = max(1, min(workers, len(processos) or 1))
        if k <= 1:
            resultado = await _processar_lista(login_page, processos, log, on_processo)
        else:
            # round-robin -> fatias balanceadas
            fatias = [processos[i::k] for i in range(k)]
            paginas = [login_page] + [await ctx.new_page() for _ in range(k - 1)]
            partes = await asyncio.gather(*[
                _processar_lista(paginas[i], fatias[i], log, on_processo)
                for i in range(k)
            ])
            for parte in partes:
                resultado.update(parte)

        try:  # logout best-effort
            await login_page.hover("text=Paulo")
            await login_page.wait_for_timeout(400)
            await login_page.locator("[id='logout']").click(timeout=4000)
        except Exception:
            pass
        await browser.close()
    return resultado
