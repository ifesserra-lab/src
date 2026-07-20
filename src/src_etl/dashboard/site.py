"""Gera o mini-site estático do campus (multi-página) a partir do consolidado.

Páginas geradas (em torno do painel index.html):
  - acoes/<acao_id>.html ......... uma página por ação/processo, com atividades
  - acoes/index.html ............. página geral: resumo do que foi feito
  - busca.html ................... busca de coordenadores(as) -> suas ações
  - sem-participacao.html ........ ações sem participações, com coordenador
  - pendencias-relatorio.html .... ações sem relatório aprovado, com coordenador

Privacidade: público-alvo aparece APENAS como contagens/situação (nunca nomes
ou CPF). A equipe executora é listada por nome + função (crédito de execução,
como em certificados públicos), sem CPF/e-mail/nascimento.
"""

from __future__ import annotations

import json
from collections import Counter
from html import escape
from pathlib import Path

from .painel import HORIZON_CSS, montar_shell
from .relatorio import _barras, _donut, _tile as _tiler, _secao, _ranking_coord
from .jornada import agregar_jornada, svg_curva_fase, svg_funil, svg_timeline

_EXTRA_CSS = """
table.tb{width:100%;border-collapse:collapse;font-size:13px}
table.tb th{color:var(--muted);text-align:left;padding:8px 10px;border-bottom:1px solid var(--border);
font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
position:sticky;top:0;background:var(--surface-1)}
table.tb td{padding:8px 10px;border-bottom:1px solid var(--grid);vertical-align:top}
table.tb tr:last-child td{border-bottom:0}
table.tb tbody tr{transition:background .15s}
table.tb tbody tr:hover{background:var(--row-hover)}
a.lk{color:var(--series-1);text-decoration:none;font-weight:500}
a.lk:hover{text-decoration:underline}
a.lk:focus-visible{outline:2px solid var(--accent-focus);outline-offset:2px}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin:14px 0}
.meta div{background:var(--surface-1);border:1px solid var(--grid);border-radius:var(--radius);
padding:11px 14px;font-size:13px}
.meta b{display:block;color:var(--muted);font-size:11px;font-weight:600;letter-spacing:.05em;
text-transform:uppercase;margin-bottom:3px}
.resumo{background:var(--surface-1);border:1px solid var(--grid);
border-left:3px solid var(--series-1);border-radius:var(--radius);padding:24px 28px;
color:var(--text-primary);max-width:none;min-height:120px;line-height:1.7;font-size:16px}
input.busca{width:100%;padding:12px 18px;border-radius:var(--radius);border:1px solid var(--border);
background:var(--surface-1);color:var(--text-primary);font-size:15px;
outline:none;font-family:inherit;transition:border-color .15s,box-shadow .15s;min-height:46px}
input.busca:focus{border-color:var(--series-1);
box-shadow:0 0 0 3px color-mix(in srgb,var(--series-1) 20%,transparent)}
input[type=search]:focus-visible{outline:2px solid var(--accent-focus);outline-offset:1px}
.busca-intro{text-align:center;max-width:64ch;margin:22px auto 4px;
color:var(--text-secondary);font-size:15px}
td.nowrap{white-space:nowrap}
.badge{display:inline-block;border:1px solid var(--grid);border-radius:6px;padding:3px 10px;
font-size:11.5px;font-weight:500;color:var(--text-secondary);white-space:nowrap;
background:var(--surface-1)}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:11.5px;font-weight:600;
white-space:nowrap;border:1px solid transparent;line-height:1.5}
.pill-c1{color:var(--c1);background:color-mix(in srgb,var(--c1) 12%,transparent);border-color:color-mix(in srgb,var(--c1) 28%,transparent)}
.pill-c2{color:var(--c2);background:color-mix(in srgb,var(--c2) 12%,transparent);border-color:color-mix(in srgb,var(--c2) 28%,transparent)}
.pill-c3{color:var(--c3);background:color-mix(in srgb,var(--c3) 14%,transparent);border-color:color-mix(in srgb,var(--c3) 30%,transparent)}
.pill-c4{color:var(--c4);background:color-mix(in srgb,var(--c4) 12%,transparent);border-color:color-mix(in srgb,var(--c4) 28%,transparent)}
.pill-c5{color:var(--c5);background:color-mix(in srgb,var(--c5) 12%,transparent);border-color:color-mix(in srgb,var(--c5) 28%,transparent)}
.pill-c6{color:var(--c6);background:color-mix(in srgb,var(--c6) 12%,transparent);border-color:color-mix(in srgb,var(--c6) 28%,transparent)}
.pill-n{color:var(--muted);background:color-mix(in srgb,var(--muted) 10%,transparent);border-color:var(--grid)}
.tl-t{fill:var(--text-primary);font-size:14px;font-weight:600}
.tl-s{fill:var(--muted);font-size:12px}
.mkt{margin-top:18px;overflow:hidden}
.mkt-head{display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin-bottom:8px}
.mkt-num{font-size:56px;font-weight:800;line-height:1;letter-spacing:-.02em;
color:var(--series-1);font-variant-numeric:tabular-nums}
.mkt-lbl{font-size:18px;line-height:1.4;color:var(--text-primary)}
.mk-svg{margin-top:6px}
.mk-ax{fill:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.mk-val{fill:var(--text-primary);font-size:12.5px;font-weight:700;font-variant-numeric:tabular-nums}
@media (max-width:560px){.mkt-num{font-size:40px}.mkt-lbl{font-size:15px}}
"""


def _doc(titulo_tab: str, base: str, ativo: str, crumb: str,
         titulo: str, sub: str, conteudo: str, hero: bool = False) -> str:
    """Documento completo no layout minimalista (topbar + conteúdo)."""
    shell = montar_shell(base, ativo, crumb, titulo, sub, conteudo, hero=hero)
    return (f"<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(titulo_tab)}</title><style>{HORIZON_CSS}{_EXTRA_CSS}</style></head>"
            f"<body>{shell}</body></html>")


def _tile(valor, rotulo, sub="") -> str:
    s = f'<div class="tile-sub">{escape(sub)}</div>' if sub else ""
    return (f'<div class="tile"><div class="tile-val">{valor}</div>'
            f'<div class="tile-lbl">{escape(rotulo)}</div>{s}</div>')


def _pill_tipo(tipo) -> str:
    """Chip colorido para o tipo da ação (cor semântica por tipo)."""
    t = (tipo or "").strip()
    tl = t.lower()
    classe = ("pill-c1" if "curso" in tl else "pill-c3" if "evento" in tl
              else "pill-c4" if "projeto" in tl else "pill-c2" if "programa" in tl
              else "pill-c5" if ("oficina" in tl or "produto" in tl) else "pill-n")
    return f'<span class="pill {classe}">{escape(t or "—")}</span>'


def _pill_natureza(nat) -> str:
    """Chip colorido para a natureza (Extensão / Ensino)."""
    t = (nat or "").strip()
    tl = t.lower()
    classe = "pill-c2" if "extens" in tl else "pill-c5" if "ensino" in tl else "pill-n"
    return f'<span class="pill {classe}">{escape(t or "—")}</span>'




def _link_pessoa(nome, base: str, slugs: dict) -> str:
    """Nome de pessoa vira link para a página do extensionista (quando existir)."""
    from .extensionistas import _norm
    slug = slugs.get(_norm(nome or ""))
    rot = escape((nome or "—").strip() or "—")
    return (f'<a class="lk" href="{base}extensionistas/{slug}.html">{rot}</a>'
            if slug else rot)


# ------------------------------------------------------------- página por ação
def _agrupar_atividades(a: dict) -> dict[str, dict]:
    """Agrupa as participações de uma ação por atividade."""
    from collections import Counter as _C
    ativm: dict[str, dict] = {}
    for p in a.get("participacoes", []):
        k = p.get("atividade_id") or "?"
        m = ativm.setdefault(k, {"num": p.get("atividade_num"), "nome": p.get("atividade"),
                                 "pub": 0, "eq": [], "aprov": 0, "cert": 0, "situ": _C()})
        if p.get("tipo", "").startswith("Público"):
            m["pub"] += 1
            situ = (p.get("Situação") or "—").strip().upper() or "—"
            m["situ"][situ] += 1
            if situ == "APROVADO":
                m["aprov"] += 1
            c = (p.get("Certificado") or "").strip().lower()
            if c and c not in ("não", "nao", "-"):
                m["cert"] += 1
        else:
            m["eq"].append(p)
    return ativm


def _pagina_acao(a: dict, slugs: dict) -> str:
    ativm = _agrupar_atividades(a)
    linhas = []
    for k, m in sorted(ativm.items(), key=lambda kv: kv[1]["num"] or ""):
        linhas.append(
            f"<tr><td>{escape(m['num'] or '—')}</td>"
            f'<td><a class="lk" href="../atividades/{escape(str(k))}.html">'
            f"{escape((m['nome'] or '—')[:90])}</a></td>"
            f"<td>{m['pub']}</td><td>{m['aprov']}</td><td>{m['cert']}</td><td>{len(m['eq'])}</td></tr>")
    tabela_ativ = (f'<div class="card" style="margin-top:14px"><table class="tb">'
                   f'<tr><th>Nº</th><th>Atividade</th><th>Público</th><th>Aprovados</th>'
                   f'<th>Certificados</th><th>Equipe</th></tr>{"".join(linhas)}</table></div>'
                   if linhas else '<div class="card"><p class="vazio">Sem atividades com participações registradas.</p></div>')

    # equipe única (nome + função), sem PII sensível
    equipe: dict[str, set] = {}
    for p in a.get("participacoes", []):
        if not p.get("tipo", "").startswith("Público"):
            equipe.setdefault((p.get("Nome") or "—").strip(), set()).add(
                (p.get("Função") or "—").strip())
    eq_rows = "".join(
        f"<tr><td>{_link_pessoa(n, '../', slugs)}</td><td>{escape(', '.join(sorted(f)))}</td></tr>"
        for n, f in sorted(equipe.items()))
    tabela_eq = (f'<div class="card" style="margin-top:14px"><table class="tb">'
                 f'<tr><th>Equipe de execução</th><th>Função(ões)</th></tr>{eq_rows}</table></div>'
                 if eq_rows else "")

    pub_total = sum(m["pub"] for m in ativm.values())
    meta = f"""<div class="meta">
<div><b>Processo</b>{escape(a.get('Processo nº') or '—')}</div>
<div><b>Coordenador(a)</b>{_link_pessoa(a.get('Coordenador(a)'), '../', slugs)}</div>
<div><b>Natureza / Tipo</b>{_pill_natureza(a.get('Natureza'))} {_pill_tipo(a.get('Tipo ação'))}</div>
<div><b>Fomento</b>{escape(a.get('Fomento') or '—')}</div>
<div><b>Cadastro</b>{escape(a.get('Data de cadastro') or '—')}</div>
<div><b>Relatório aprovado</b>{escape(a.get('Relatório aprovado') or '—')}</div>
</div>"""
    resumo = (f'<div class="resumo">{escape(a.get("Resumo") or "Sem resumo cadastrado.")}</div>')
    tiles = (f'<div class="tiles">{_tile(len(ativm), "Atividades")}'
             f'{_tile(pub_total, "Alunos atendidos", "participações de público")}'
             f'{_tile(len(equipe), "Pessoas na equipe")}</div>')

    conteudo = (f"{meta}{resumo}{tiles}{tabela_ativ}{tabela_eq}"
                f"<div class='pii'>Público-alvo é mostrado apenas como contagem — nomes, CPF e "
                f"e-mail de alunos atendidos não são publicados. A equipe de execução é listada "
                f"como crédito público (sem dados pessoais).</div>")
    return _doc(a.get("Título ação") or "Ação", "../", "", "Ação",
                a.get("Título ação") or "Ação",
                f"Ação do SRC/Ifes — Campus {a.get('Campus') or a.get('campus') or ''}",
                conteudo)


# ------------------------------------------------------------- página por atividade
def _pagina_atividade(a: dict, aid: str, m: dict, slugs: dict) -> str:
    """Página de UMA atividade: contexto da ação-mãe + números + equipe nominal."""
    situ_rows = "".join(f"<tr><td>{escape(s)}</td><td>{n}</td></tr>"
                        for s, n in m["situ"].most_common())
    tiles = (f'<div class="tiles">{_tile(m["pub"], "Alunos atendidos")}'
             f'{_tile(m["aprov"], "Aprovados")}'
             f'{_tile(m["cert"], "Certificados emitidos")}'
             f'{_tile(len(m["eq"]), "Equipe")}</div>')
    meta = f"""<div class="meta">
<div><b>Ação</b><a class="lk" href="../acoes/{escape(str(a.get('acao_id')))}.html">{escape((a.get('Título ação') or '—')[:70])}</a></div>
<div><b>Processo</b>{escape(a.get('Processo nº') or '—')}</div>
<div><b>Coordenador(a) da ação</b>{_link_pessoa(a.get('Coordenador(a)'), '../', slugs)}</div>
<div><b>Nº da atividade</b>{escape(m['num'] or '—')}</div>
</div>"""
    blocos = [meta, tiles]
    if situ_rows:
        blocos.append(f'<div class="card" style="margin-top:14px"><h2>Situação do público-alvo</h2>'
                      f'<table class="tb"><tr><th>Situação</th><th>Participantes</th></tr>{situ_rows}</table></div>')
    if m["eq"]:
        eq_rows = "".join(
            f"<tr><td>{_link_pessoa(p.get('Nome'), '../', slugs)}</td>"
            f"<td>{escape((p.get('Função') or '—').strip())}</td>"
            f"<td>{escape((p.get('Vínculo') or '—').strip())}</td></tr>"
            for p in sorted(m["eq"], key=lambda x: (x.get("Nome") or "")))
        blocos.append(f'<div class="card" style="margin-top:14px"><h2>Equipe de execução</h2>'
                      f'<table class="tb"><tr><th>Nome</th><th>Função</th><th>Vínculo</th></tr>{eq_rows}</table></div>')
    blocos.append('<div class="pii">Público-alvo apenas como contagens — sem nomes, CPF ou '
                  'e-mail de alunos. Equipe listada como crédito público de execução.</div>')
    return _doc(m["nome"] or "Atividade", "../", "", "Atividade",
                m["nome"] or "Atividade",
                f"Atividade da ação · Campus {a.get('Campus') or a.get('campus') or ''}",
                "".join(blocos))


# ------------------------------------------------------------- página geral
def _pagina_geral(cons: dict, slugs: dict) -> str:
    acoes = cons["acoes"]
    profs = set()
    alunos_cpf = set()
    for a in acoes:
        for p in a.get("participacoes", []):
            if p.get("tipo", "").startswith("Público"):
                if p.get("CPF"):
                    alunos_cpf.add(p["CPF"])
            elif "PROFESSOR" in (p.get("Função") or "").upper():
                profs.add((p.get("Nome") or "").strip())
    coords = {(a.get("Coordenador(a)") or "—").strip() for a in acoes}

    tiles = (f'<div class="tiles">{_tile(cons["total_acoes"], "Ações")}'
             f'{_tile(cons["total_atividades"], "Atividades")}'
             f'{_tile(cons["total_publico_alvo"], "Participações de alunos")}'
             f'{_tile(len(alunos_cpf), "Alunos únicos")}'
             f'{_tile(len(coords), "Coordenadores(as)")}'
             f'{_tile(len(profs), "Professores na execução")}</div>')

    rows = "".join(
        f'<tr><td><a class="lk" href="{escape(str(a.get("acao_id")))}.html">'
        f'{escape((a.get("Título ação") or "—")[:80])}</a></td>'
        f'<td>{_pill_tipo(a.get("Tipo ação"))}</td>'
        f'<td>{_link_pessoa(a.get("Coordenador(a)"), "../", slugs)}</td>'
        f'<td>{a.get("total_participacoes", 0)}</td>'
        f'<td><span class="badge">{escape((a.get("Data de cadastro") or "—")[-4:])}</span></td></tr>'
        for a in sorted(acoes, key=lambda x: -(x.get("total_participacoes") or 0)))
    tabela = (f'<div class="card" style="margin-top:16px"><table class="tb" id="tb-acoes">'
              f'<tr><th>Ação</th><th>Tipo</th><th>Coordenador(a)</th>'
              f'<th>Participações</th><th>Ano</th></tr>{rows}</table></div>')
    tabela = _com_busca("tb-acoes", "Filtrar por ação, coordenador(a), tipo ou ano...", tabela)

    return _doc("Ações — Campus Serra", "../", "acoes/index.html", "Ações",
                "O que foi feito — Campus Serra",
                "Resumo geral das ações de extensão e ensino registradas no SRC",
                f"{tiles}{tabela}")


# ------------------------------------------------------------- marketing
def _pessoas_por_ano(cons: dict) -> tuple[list[tuple[str, int]], int, int]:
    """(pares [(ano, pessoas distintas)], total distinto, total atendimentos).

    Pessoas atingidas = público-alvo distinto (por CPF/nome, uso interno) no ano
    do atendimento (data de início; cai para o ano de cadastro da ação)."""
    import re
    per: dict[str, set] = {}
    total: set = set()
    atend = 0
    for a in cons["acoes"]:
        ano_acao = (a.get("Data de cadastro") or "")[-4:]
        for p in a.get("participacoes", []):
            if not (p.get("tipo") or "").startswith("Públic"):
                continue
            atend += 1
            m = re.search(r"(\d{4})\s*$", (p.get("Início") or "").strip())
            ano = m.group(1) if m else ano_acao
            if not (ano and ano.isdigit()):
                continue
            pid = p.get("CPF") or p.get("Nome") or f"?{atend}"
            per.setdefault(ano, set()).add(pid)
            total.add(pid)
    pares = [(y, len(per[y])) for y in sorted(per)]
    return pares, len(total), atend


def _svg_area_anos(pares: list[tuple[str, int]]) -> str:
    """Gráfico de área/linha: pessoas atingidas ao longo dos anos (marketing)."""
    if not pares:
        return ""
    W, H = 1000, 300
    pl, pr, pt, pb = 24, 24, 34, 46
    iw, ih = W - pl - pr, H - pt - pb
    n = len(pares)
    mx = max(v for _, v in pares) or 1
    pts = []
    for i, (ano, v) in enumerate(pares):
        x = pl + (iw * i / (n - 1) if n > 1 else iw / 2)
        y = pt + ih * (1 - v / mx)
        pts.append((x, y, ano, v))
    linha = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in pts)
    area = f"{pts[0][0]:.1f},{pt+ih:.0f} {linha} {pts[-1][0]:.1f},{pt+ih:.0f}"
    # gridlines suaves (sem números no eixo y — visual de marketing)
    grid = [f'<line x1="{pl}" y1="{pt+ih*frac:.0f}" x2="{W-pr}" y2="{pt+ih*frac:.0f}" '
            f'stroke="var(--grid)" stroke-width="1"/>' for frac in (0.0, 0.5, 1.0)]
    # rótulos do eixo x (anos) — todos se poucos, senão espaçados
    passo = 1 if n <= 12 else (n // 10 + 1)
    xlab = "".join(
        f'<text x="{pts[i][0]:.1f}" y="{H-16}" text-anchor="middle" class="mk-ax">{pts[i][2]}</text>'
        for i in range(n) if i % passo == 0 or i == n - 1)
    # pontos + destaque do maior e do último
    i_max = max(range(n), key=lambda i: pts[i][3])
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="transparent">'
                   f'<title>{ano}: {v} pessoas atingidas</title></circle>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="var(--series-1)"/>'
                   f'<text x="{x:.1f}" y="{y-11:.1f}" text-anchor="middle" class="mk-val">{v}</text>'
                   for x, y, ano, v in pts)
    def bolha(i, cor):
        x, y, ano, v = pts[i]
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{cor}" '
                f'stroke="var(--surface-1)" stroke-width="2.5"/>')
    destaque = bolha(i_max, "var(--cta)") + (bolha(n-1, "var(--series-1)") if n-1 != i_max else "")
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" class="mk-svg" '
            f'style="display:block">'
            f'<defs><linearGradient id="mkg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="var(--series-1)" stop-opacity="0.35"/>'
            f'<stop offset="1" stop-color="var(--series-1)" stop-opacity="0"/></linearGradient></defs>'
            + "".join(grid)
            + f'<polygon points="{area}" fill="url(#mkg)"/>'
            + f'<polyline points="{linha}" fill="none" stroke="var(--series-1)" stroke-width="2.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            + dots + destaque + xlab + '</svg>')


def _bloco_marketing(cons: dict) -> str:
    pares, total, atend = _pessoas_por_ano(cons)
    if not pares:
        return ""
    anos = f"{pares[0][0]}–{pares[-1][0]}"
    n_fmt = f"{total:,}".replace(",", ".")
    at_fmt = f"{atend:,}".replace(",", ".")
    return (
        '<div class="mkt card">'
        '<div class="mkt-head">'
        f'<div class="mkt-num">+{n_fmt}</div>'
        '<div class="mkt-lbl"><b>pessoas atingidas</b> pela extensão do Campus Serra'
        f'<br><span class="sec-desc">em {escape(anos)} · {at_fmt} atendimentos em '
        'cursos, eventos e projetos</span></div>'
        '</div>'
        + _svg_area_anos(pares) +
        '<p class="sec-desc" style="margin:10px 2px 0">Pessoas atingidas por ano '
        '(público-alvo distinto).</p>'
        '</div>')


# ------------------------------------------------------------- busca
def _pagina_busca(cons: dict, slugs: dict, pessoas: list[dict] | None = None) -> str:
    """Busca por palavras-chave: ações E extensionistas (iniciativas/participações)."""
    from .extensionistas import _norm as _n
    idx = []
    for a in cons["acoes"]:
        area = (a.get("Área temática principal") or a.get("Área temática principal (inferida)") or "")
        ga = (a.get("Grande área conhecimento") or a.get("Grande área conhecimento (inferida)") or "")
        idx.append({
            "id": a.get("acao_id"),
            "t": (a.get("Título ação") or "—")[:90],
            "c": (a.get("Coordenador(a)") or "—").strip(),
            "cs": slugs.get(_n(a.get("Coordenador(a)") or "")),
            "tp": a.get("Tipo ação") or "—",
            "ano": (a.get("Data de cadastro") or "")[-4:],
            "n": a.get("total_participacoes", 0),
            # blob de busca: tudo que pode ser palavra-chave
            "b": " ".join([
                a.get("Título ação") or "", a.get("Coordenador(a)") or "",
                a.get("Tipo ação") or "", a.get("Natureza") or "",
                area, ga, a.get("Fomento") or "", a.get("Processo nº") or "",
                (a.get("Resumo") or "")[:400]]),
        })
    # índice de pessoas: iniciativas (ações), participações e pessoas impactadas
    pidx = []
    for p in (pessoas or []):
        ppa = _projetos_por_ano(p)
        pidx.append({
            "s": p["slug"], "nome": p["nome"],
            "f": ", ".join(p.get("funcoes", [])[:4]),
            "a": sum(r[1] for r in ppa), "p": sum(r[2] for r in ppa),
            "i": sum(r[3] for r in ppa),
            "b": " ".join([p["nome"]] + list(p.get("funcoes", []))),
        })
    # índice de atividades (as iniciativas dentro de cada ação)
    aidx = []
    for a in cons["acoes"]:
        titulo = a.get("Título ação") or "—"
        for aid, m in _agrupar_atividades(a).items():
            if not aid or aid == "?":
                continue
            nome = m.get("nome") or "—"
            aidx.append({
                "id": aid, "nome": nome[:80], "acao": titulo[:70],
                "ano": (a.get("Data de cadastro") or "")[-4:],
                "n": m.get("pub", 0) + len(m.get("eq", [])),
                "b": " ".join([nome, titulo, a.get("Tipo ação") or "",
                               a.get("Coordenador(a)") or "", a.get("Natureza") or ""]),
            })
    dados = json.dumps(idx, ensure_ascii=False)
    dados_pes = json.dumps(pidx, ensure_ascii=False)
    dados_atv = json.dumps(aidx, ensure_ascii=False)
    script = """
<script>
const IDX = __DADOS__, PES = __PESSOAS__, ATV = __ATV__;
const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
function pill(t){const l=norm(t||'');const c=l.includes('curso')?'c1':l.includes('evento')?'c3':l.includes('projeto')?'c4':l.includes('programa')?'c2':(l.includes('oficina')||l.includes('produto'))?'c5':'n';return `<span class="pill pill-${c}">${t||'—'}</span>`;}
IDX.forEach(a => a.nb = norm(a.b));
PES.forEach(p => p.nb = norm(p.b));
ATV.forEach(a => a.nb = norm(a.b));
const inp = document.getElementById('q'), out = document.getElementById('res');
function render(q){
  out.innerHTML='';
  const termos = norm(q.trim()).split(/\\s+/).filter(t=>t.length>=2);
  if(!termos.length){out.innerHTML='<p class="vazio">Digite palavras-chave: tema (robótica, inglês, saúde), coordenador(a)/extensionista, atividade, tipo (curso, evento), fomento, ano...</p>';return;}
  const pes = PES.filter(p => termos.every(t => p.nb.includes(t))).sort((x,y)=>y.p-x.p);
  const hits = IDX.filter(a => termos.every(t => a.nb.includes(t))).sort((x,y)=>y.n-x.n);
  const atv = ATV.filter(a => termos.every(t => a.nb.includes(t))).sort((x,y)=>y.n-x.n);
  let h = '';
  if(pes.length){
    h += `<div class="card" style="margin-top:14px"><p class="sec-desc">${pes.length} extensionista(s) — iniciativas e participações</p><table class="tb"><tr><th>Extensionista</th><th>Funções</th><th>Iniciativas</th><th>Participações</th><th>Pessoas impactadas</th></tr>`;
    for(const p of pes)
      h += `<tr><td><a class="lk" href="extensionistas/${p.s}.html">${p.nome}</a></td><td>${p.f||'—'}</td><td>${p.a}</td><td>${p.p}</td><td>${p.i}</td></tr>`;
    h += '</table></div>';
  }
  if(hits.length){
    h += `<div class="card" style="margin-top:14px"><p class="sec-desc">${hits.length} ação(ões) — iniciativas de extensão</p><table class="tb"><tr><th>Ação</th><th>Coordenador(a)</th><th>Tipo</th><th>Ano</th><th>Participações</th></tr>`;
    for(const a of hits)
      h += `<tr><td><a class="lk" href="acoes/${a.id}.html">${a.t}</a></td><td>${a.cs?`<a class="lk" href="extensionistas/${a.cs}.html">${a.c}</a>`:a.c}</td><td>${pill(a.tp)}</td><td>${a.ano}</td><td>${a.n}</td></tr>`;
    h += '</table></div>';
  }
  if(atv.length){
    const lim = atv.slice(0,200);
    h += `<div class="card" style="margin-top:14px"><p class="sec-desc">${atv.length} atividade(s)${atv.length>200?' (200 primeiras)':''}</p><table class="tb"><tr><th>Atividade</th><th>Ação</th><th>Ano</th><th>Participações</th></tr>`;
    for(const a of lim)
      h += `<tr><td><a class="lk" href="atividades/${a.id}.html">${a.nome}</a></td><td>${a.acao}</td><td>${a.ano}</td><td>${a.n}</td></tr>`;
    h += '</table></div>';
  }
  out.innerHTML = h || '<p class="vazio">Nada encontrado para esses termos. Tente palavras mais gerais.</p>';
}
inp.addEventListener('input', e=>render(e.target.value)); render('');
</script>""".replace("__DADOS__", dados).replace("__PESSOAS__", dados_pes).replace("__ATV__", dados_atv)
    chips = "".join(f'<button data-q="{c}">{c}</button>'
                    for c in ["robótica", "inglês", "saúde", "curso 2024", "cultura", "FAPES"])
    script += """
<script>
document.querySelectorAll('.chips button').forEach(b=>b.addEventListener('click',()=>{
  const q=document.getElementById('q'); q.value=b.dataset.q;
  q.dispatchEvent(new Event('input')); q.focus();
}));
</script>"""
    intro = ("Busque nas 201 ações e nos extensionistas por palavras-chave — título, resumo, "
             "coordenador(a), tipo, área temática, fomento, processo; veja iniciativas e "
             "participações de cada pessoa")
    conteudo = (f'{_bloco_marketing(cons)}'
                f'<p class="sub busca-intro">{escape(intro)}</p>'
                f'<input class="busca" id="q" type="search" '
                f'placeholder="Busque por tema, extensionista, tipo, fomento, ano..."'
                f'><div class="chips">{chips}</div>'
                f'<div id="res"></div>{script}')
    return _doc("SRC · Campus Serra — Buscar", "", "index.html", "Buscar",
                "O que a extensão do Campus Serra já fez?",
                "",
                conteudo, hero=True)


# ------------------------------------------------------------- listas de gestão
def _com_busca(tid: str, placeholder: str, card_html: str) -> str:
    """Envolve uma tabela (com id=tid) com um filtro client-side por palavras."""
    inp = (f'<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:8px 0 4px">'
           f'<input id="f-{tid}" type="search" placeholder="{escape(placeholder)}" '
           f'style="flex:1;min-width:240px;padding:11px 15px;font-size:15px;'
           f'border:1px solid var(--border);border-radius:var(--radius-sm);'
           f'background:var(--surface-1);color:var(--text-primary)">'
           f'<span class="sec-desc" id="c-{tid}" style="margin:0;white-space:nowrap"></span></div>')
    js = ("<script>(function(){"
          f"var inp=document.getElementById('f-{tid}'),tb=document.getElementById('{tid}');"
          "if(!inp||!tb)return;"
          "var norm=function(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();};"
          "var rows=Array.prototype.slice.call(tb.rows).filter(function(r){return !r.querySelector('th');});"
          f"var cnt=document.getElementById('c-{tid}');"
          "function upd(){var ts=norm(inp.value.trim()).split(/\\s+/).filter(Boolean),v=0;"
          "rows.forEach(function(r){var t=norm(r.textContent);"
          "var ok=ts.every(function(x){return t.indexOf(x)>=0;});"
          "r.style.display=ok?'':'none';if(ok)v++;});"
          "if(cnt)cnt.textContent=v+' de '+rows.length;}"
          "inp.addEventListener('input',upd);upd();"
          "})();</script>")
    return inp + card_html + js


def _tabela_acoes(itens: list[dict], slugs: dict, extra_col: tuple[str, str] | None = None,
                  tid: str = "tb", *, relatorio: bool = False) -> str:
    cab = "<tr><th>Ação</th><th>Tipo</th><th>Coordenador(a)</th><th>Ano</th>"
    cab += f"<th>{escape(extra_col[0])}</th>" if extra_col else ""
    cab += "<th>Modelo de relatório</th></tr>" if relatorio else "</tr>"
    rows = []
    for it in itens:
        extra = f"<td>{escape(str(it.get(extra_col[1]) or '—'))}</td>" if extra_col else ""
        rel = ""
        if relatorio:
            aid = escape(str(it.get("acao_id")))
            rel = (f'<td class="nowrap"><a class="lk" href="relatorios-odt/{aid}.pdf">PDF</a>'
                   f' · <a class="lk" href="relatorios-odt/{aid}.odt">ODT</a></td>')
        rows.append(
            f'<tr><td><a class="lk" href="acoes/{escape(str(it.get("acao_id")))}.html">'
            f'{escape((it.get("titulo") or "—")[:75])}</a></td>'
            f'<td>{_pill_tipo(it.get("tipo"))}</td>'
            f'<td>{_link_pessoa(it.get("coordenador"), "", slugs)}</td>'
            f'<td>{escape(it.get("ano") or "—")}</td>{extra}{rel}</tr>')
    return (f'<div class="card" style="margin-top:16px"><table class="tb" id="{tid}">'
            f'{cab}{"".join(rows)}</table></div>')


def _pagina_sem_participacao(cons: dict, slugs: dict) -> str:
    itens = []
    for a in cons["acoes"]:
        if a.get("total_participacoes", 0) == 0:
            itens.append({"acao_id": a.get("acao_id"),
                          "titulo": a.get("Título ação"),
                          "tipo": a.get("Tipo ação"),
                          "coordenador": (a.get("Coordenador(a)") or "—").strip(),
                          "ano": (a.get("Data de cadastro") or "")[-4:]})
    itens.sort(key=lambda x: (x["coordenador"], x["ano"]))
    tabela = _com_busca("tb-sem", "Filtrar por ação, coordenador(a), tipo ou ano...",
                        _tabela_acoes(itens, slugs, tid="tb-sem"))
    # ranking de coordenadores com ações sem participação (vindo do painel)
    coord_total = Counter((a.get("Coordenador(a)") or "—").strip() or "—" for a in cons["acoes"])
    coord_sem = Counter(x["coordenador"] or "—" for x in itens)
    rank = [(nome, n, coord_total[nome]) for nome, n in coord_sem.most_common(12)]
    ranking = ('<section style="margin-top:20px"><h2>Coordenadores com ações sem participação</h2>'
               '<p class="sec-desc">Nº de ações sem participação por coordenador(a) e proporção do '
               'total dele(a) — proporção alta sugere não-registro sistemático; baixa, caso pontual.</p>'
               f'<div class="card">{_ranking_coord(rank)}</div></section>')
    return _doc("Ações sem participações — Campus Serra", "", "sem-participacao.html",
                "Sem participações", f"Ações sem participações ({len(itens)})",
                "Ações sem nenhum público-alvo nem equipe registrados no SRC — "
                "pendência de registro a regularizar com o(a) coordenador(a)",
                tabela + ranking)


def _tabela_pend(itens: list[dict], slugs: dict, tid: str) -> str:
    """Tabela de pendências: Ação · Tipo · Coord · Ano · Público · Equipe · Últ. relatório · Modelo."""
    cab = ("<tr><th>Ação</th><th>Tipo</th><th>Coordenador(a)</th><th>Início</th><th>Término</th>"
           "<th>Público</th><th>Equipe</th><th>Últ. relatório</th><th>Modelo de relatório</th></tr>")
    rows = []
    for it in itens:
        aid = escape(str(it.get("acao_id")))
        rows.append(
            f'<tr><td><a class="lk" href="acoes/{aid}.html">{escape((it.get("titulo") or "—")[:70])}</a></td>'
            f'<td>{_pill_tipo(it.get("tipo"))}</td>'
            f'<td>{_link_pessoa(it.get("coordenador"), "", slugs)}</td>'
            f'<td class="nowrap">{escape(it.get("inicio") or "—")}</td>'
            f'<td class="nowrap">{escape(it.get("termino") or "—")}</td>'
            f'<td>{it.get("pub", 0)}</td><td>{it.get("eq", 0)}</td>'
            f'<td>{escape(it.get("ultimo") or "—")}</td>'
            f'<td class="nowrap"><a class="lk" href="relatorios-odt/{aid}.pdf">PDF</a>'
            f' · <a class="lk" href="relatorios-odt/{aid}.odt">ODT</a></td></tr>')
    return (f'<div class="card" style="margin-top:16px"><table class="tb" id="{tid}">'
            f'{cab}{"".join(rows)}</table></div>')


def _pagina_pendencias(cons: dict, slugs: dict) -> str:
    itens = []
    for a in cons["acoes"]:
        if (a.get("Relatório aprovado") or "").strip().lower() == "sim":
            continue
        from datetime import datetime as _dt

        def _d(s):
            try:
                return _dt.strptime((s or "").strip(), "%d/%m/%Y")
            except (ValueError, AttributeError):
                return None
        pub, eq = set(), set()
        inis, terms = [], []
        for p in a.get("participacoes", []):
            di, dtm = _d(p.get("Início")), _d(p.get("Término"))
            if di:
                inis.append(di)
            if dtm:
                terms.append(dtm)
            if (p.get("tipo") or "").startswith("Públic"):
                pid = p.get("CPF") or p.get("Nome")
                if pid:
                    pub.add(pid)
            else:
                nm = (p.get("Nome") or "").strip()
                if nm:
                    eq.add(nm)
        itens.append({"acao_id": a.get("acao_id"), "titulo": a.get("Título ação"),
                      "tipo": a.get("Tipo ação"),
                      "coordenador": (a.get("Coordenador(a)") or "—").strip(),
                      "ano": (a.get("Data de cadastro") or "")[-4:],
                      "inicio": min(inis).strftime("%d/%m/%Y") if inis else "",
                      "termino": max(terms).strftime("%d/%m/%Y") if terms else "",
                      "ultimo": a.get("Data último relatório") or "nunca enviado",
                      "pub": len(pub), "eq": len(eq)})
    itens.sort(key=lambda x: (x["coordenador"], x["ano"]))
    com = [x for x in itens if x["pub"] + x["eq"] > 0]
    zero = [x for x in itens if x["pub"] + x["eq"] == 0]
    top = "".join(f'<span class="badge" style="margin:3px">{escape(n)}: {q}</span>'
                  for n, q in Counter(i["coordenador"] for i in itens).most_common(12))
    ajuda = ('<div class="pii" style="margin-top:0">'
             '<b>Como regularizar.</b> Cada linha traz o <b>Relatório de Ação de Extensão</b> '
             '(modelo oficial da PROEX, ON CAEx 01-2020) já <b>pré-preenchido</b> com os dados do '
             'SRC (título, coordenador(a), datas, área e nº de participantes) e traz uma '
             '<b>sugestão de rascunho</b> no campo "Resultados e impactos" (gerada por IA — '
             '<b>revise antes de enviar</b>) — baixe em <b>PDF</b> ou <b>ODT</b>, complete os '
             'campos qualitativos e entregue à CGAEx. '
             'Prazo: relatório final em até 30 dias após o término; parcial, anualmente entre '
             '1º/nov e 15/dez. '
             '<a class="lk" href="https://forms.office.com/r/m73RLCBx5S" target="_blank" rel="noopener">'
             'Formulário eletrônico da PROEX ↗</a></div>')
    sec_com = (f'<section style="margin-top:18px"><h2>Com participação registrada ({len(com)})</h2>'
               '<p class="sec-desc">Ações que têm público-alvo e/ou equipe no SRC, mas ainda '
               'sem relatório final aprovado — prontas para gerar o relatório.</p>'
               + _com_busca("tb-pend", "Filtrar por ação, coordenador(a), tipo ou ano...",
                            _tabela_pend(com, slugs, "tb-pend")) + '</section>')
    sec_zero = (f'<section style="margin-top:26px"><h2>Sem participação registrada ({len(zero)})</h2>'
                '<p class="sec-desc">Ações pendentes com <b>público = 0 e equipe = 0</b> no SRC — '
                'antes do relatório, é preciso <b>registrar os participantes</b> (ou a ação não foi '
                'executada). Veja também a página <a class="lk" href="sem-participacao.html">Sem participações</a>.</p>'
                + _com_busca("tb-pend0", "Filtrar por ação, coordenador(a), tipo ou ano...",
                             _tabela_pend(zero, slugs, "tb-pend0")) + '</section>') if zero else ''
    return _doc("Pendências de relatório — Campus Serra", "", "pendencias-relatorio.html",
                "Pendências", f"Pendências de relatório ({len(itens)})",
                "Ações sem relatório final aprovado no SRC (inclui ações em andamento) — "
                "com o(a) coordenador(a) responsável",
                f'<div class="card">{top}</div>{ajuda}{sec_com}{sec_zero}')


# ------------------------------------------------------------- dados abertos
def _fmt_bytes(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} GB"


def _pagina_dados(out_dir: str | Path, stats: dict) -> str:
    """Página de Dados Abertos: downloads em JSON (sem PII) + llms.txt para IA."""
    out = Path(out_dir)

    def sz(rel: str) -> str:
        p = out / rel
        return _fmt_bytes(p.stat().st_size) if p.exists() else "—"

    n_ac = stats.get("paginas_acao", 0)
    n_at = stats.get("atividades", 0)
    n_ex = stats.get("extensionistas", 0)

    # destaque llms.txt (para IA)
    ia = ('<div class="card" style="margin-top:16px;border-left:3px solid var(--cta)">'
          '<h2 style="margin-top:0">Para uma IA ler: <code>llms.txt</code></h2>'
          '<p class="sec-desc">Arquivo em texto (Markdown) que descreve todos os conjuntos de '
          'dados e aponta os links — no padrão <b>llms.txt</b>, feito para modelos de IA lerem e '
          'navegarem o acervo. Cole o link num chat de IA ou baixe o arquivo.</p>'
          f'<p><a class="lk" href="llms.txt" download>⬇ Baixar llms.txt</a> · '
          f'<a class="lk" href="llms.txt">abrir</a> <span class="sec-desc">({sz("llms.txt")})</span></p>'
          '</div>')

    datasets = [
        ("Inventário da API", "api/index.json", "Índice dos endpoints e totais do acervo."),
        ("Painel agregado", "api/painel.json",
         "Visão geral, indicadores, rede de programas, formados e impacto (tudo agregado)."),
        ("Ações — lista", "api/acoes/index.json", f"As {n_ac} ações, resumidas."),
        ("Extensionistas — completo", "api/extensionistas/todos.json",
         f"As {n_ex} pessoas com trajetória (ações coordenadas/equipe) e resumo por IA."),
        ("Extensionistas — lista", "api/extensionistas/index.json", "Índice de extensionistas."),
        ("Busca — índice", "api/busca.json", "Blob de busca por palavras-chave das ações."),
        ("Ações sem participações", "api/sem-participacao.json",
         "Ações com público-alvo e equipe zerados (pendência de registro)."),
        ("Pendências de relatório", "api/pendencias-relatorio.json",
         "Ações sem relatório final aprovado."),
    ]
    rows = "".join(
        f'<tr><td><a class="lk" href="{url}" download>{escape(nome)}</a></td>'
        f'<td>{escape(desc)}</td><td>JSON</td><td>{sz(url)}</td>'
        f'<td><a class="lk" href="{url}">abrir</a></td></tr>'
        for nome, url, desc in datasets)
    tabela = (f'<div class="card" style="margin-top:16px"><h2 style="margin-top:0">Conjuntos de dados</h2>'
              f'<table class="tb"><tr><th>Conjunto</th><th>Descrição</th><th>Formato</th>'
              f'<th>Tamanho</th><th></th></tr>{rows}</table></div>')

    # endpoints por item (padrões)
    padroes = (
        '<div class="card" style="margin-top:16px"><h2 style="margin-top:0">Por item (um arquivo cada)</h2>'
        '<table class="tb"><tr><th>Padrão</th><th>O que é</th><th>Qtd.</th></tr>'
        f'<tr><td><code>api/acoes/&lt;acao_id&gt;.json</code></td><td>Uma ação + atividades + equipe.</td><td>{n_ac}</td></tr>'
        f'<tr><td><code>api/atividades/&lt;atividade_id&gt;.json</code></td><td>Uma atividade (público em contagens + equipe).</td><td>{n_at}</td></tr>'
        f'<tr><td><code>api/extensionistas/&lt;slug&gt;.json</code></td><td>Trajetória de uma pessoa + resumo IA.</td><td>{n_ex}</td></tr>'
        '</table></div>')

    priv = (
        '<div class="card" style="margin-top:16px"><h2 style="margin-top:0">Privacidade e uso</h2>'
        '<p class="sec-desc" style="line-height:1.6">'
        '<b>Sem dados pessoais de alunos.</b> Público-alvo aparece apenas como <b>contagens</b> '
        '(inscritos, aprovados, certificados, situação) — nunca nomes. A equipe executora é '
        'listada como <b>crédito público de execução</b> (nome, função, vínculo), como em '
        'certificados. <b>Nenhum arquivo contém CPF, e-mail ou data de nascimento</b> — há uma '
        'trava automática que bloqueia a exportação se qualquer PII vazar.<br><br>'
        'Fonte: SRC/Ifes (<code>src.ifes.edu.br</code>). Dados públicos institucionais de extensão '
        'e ensino. Gerado pela lib <code>src_etl</code>.</p></div>')

    como = (
        '<div class="card" style="margin-top:16px"><h2 style="margin-top:0">Como usar</h2>'
        '<pre style="overflow:auto;background:var(--parchment);padding:14px;border-radius:var(--radius-sm);'
        'font-family:var(--mono);font-size:13px;line-height:1.5"># baixar tudo de uma pessoa\n'
        'curl -s .../api/extensionistas/todos.json | jq \'.[0]\'\n\n'
        '# lista de ações\n'
        'curl -s .../api/acoes/index.json | jq \'.[] | {titulo, coordenador, ano}\'</pre>'
        '<p class="sec-desc">Troque <code>...</code> pela URL desta página. Todos os arquivos são '
        'JSON UTF-8; <code>llms.txt</code> é texto.</p></div>')

    corpo = ia + tabela + padroes + priv + como
    return _doc("Dados Abertos — Campus Serra", "", "dados-abertos.html",
                "Dados abertos",
                "Dados abertos da extensão — Campus Serra",
                "Baixe os dados em JSON (sem CPF nem e-mail) e o llms.txt para uma IA ler o acervo",
                corpo)


# ------------------------------------------------------------- extensionistas
def _ego_grafo(nome: str, colabs: list[tuple[str, str, int]]) -> str:
    """Grafo ego: pessoa central + colaboradores ao redor (aresta = nº ações)."""
    import math
    if not colabs:
        return '<p class="vazio">Sem colaboradores registrados em equipe.</p>'
    top = colabs[:12]
    W, H = 900, 460
    cx, cy, R = W / 2, H / 2, 165
    maxw = max(n for _, _, n in top) or 1
    n = len(top)
    arestas, nos = [], []
    for i, (cnome, cslug, cnt) in enumerate(top):
        ang = 2 * math.pi * i / n - math.pi / 2
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        sw = 1 + (cnt / maxw) * 5
        arestas.append(f'<line x1="{cx:.0f}" y1="{cy:.0f}" x2="{x:.0f}" y2="{y:.0f}" '
                       f'stroke="var(--series-1)" stroke-width="{sw:.1f}" stroke-opacity=".35"/>')
        curto = " ".join(cnome.split()[:2])
        anchor = "start" if x >= cx else "end"
        dx = 11 if x >= cx else -11
        alvo = f'{cslug}.html' if cslug else None
        rot = (f'<a href="{alvo}"><text x="{x+dx:.0f}" y="{y+4:.0f}" text-anchor="{anchor}" '
               f'class="net-lbl">{escape(curto)}</text></a>' if alvo else
               f'<text x="{x+dx:.0f}" y="{y+4:.0f}" text-anchor="{anchor}" class="net-lbl">{escape(curto)}</text>')
        nos.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="var(--series-1)" '
                   f'stroke="var(--surface-1)" stroke-width="2"><title>{escape(cnome)}: {cnt} ação(ões)</title></circle>{rot}')
    centro = (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="11" fill="var(--cta)" '
              f'stroke="var(--surface-1)" stroke-width="3"/>'
              f'<text x="{cx:.0f}" y="{cy-18:.0f}" text-anchor="middle" class="tl-t">'
              f'{escape(" ".join(nome.split()[:2]))}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img">'
            + "".join(arestas) + centro + "".join(nos) + "</svg>")


def _fmt_num(v: int) -> str:
    """Rótulo compacto: 1611 -> 1,6k (evita colisão em barras finas)."""
    if v >= 1000:
        return f"{v/1000:.1f}k".replace(".0k", "k").replace(".", ",")
    return str(v)


def _barras_v2(dados: list[tuple[str, int, int, int]]) -> str:
    """Barras VERTICAIS agrupadas (3 séries) preenchendo a largura.

    dados = [(ano, ações, atividades atuadas, alcance)]. Escalas independentes
    por série (magnitudes muito diferentes), com legenda e valores reais."""
    if not dados:
        return '<p class="vazio">Sem dados.</p>'
    series = [(1, "var(--series-1)", "Ações"),
              (2, "var(--series-2)", "Participações"),
              (3, "var(--cta)", "Pessoas impactadas")]
    maxs = {k: (max(row[k] for row in dados) or 1) for k, _, _ in series}
    n = len(dados)
    W, top, base_h = 1000, 20, 66           # aspecto largo -> baixo ao ocupar 100%
    H = top + base_h + 26
    slot = W / n
    bw = min(18, slot * 0.20)               # 3 barras por slot
    gap = max(3, bw * 0.28)
    grupo = bw * 3 + gap * 2
    barras = []
    for i, row in enumerate(dados):
        rot = row[0]
        cx = slot * (i + 0.5)
        x0 = cx - grupo / 2
        for j, (k, cor, nome) in enumerate(series):
            v = row[k]
            bh = max(2, round(v / maxs[k] * base_h))
            x = x0 + j * (bw + gap)
            y = top + base_h - bh
            barras.append(
                f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="3" fill="{cor}">'
                f'<title>{escape(rot)} — {nome}: {v}</title></rect>'
                f'<text x="{x+bw/2:.1f}" y="{y-5}" text-anchor="middle" class="val">{_fmt_num(v)}</text>')
        barras.append(
            f'<text x="{cx:.1f}" y="{top+base_h+18}" text-anchor="middle" class="lbl">{escape(rot)}</text>')
    legenda = ('<div class="leg" style="flex-direction:row;gap:18px;margin-top:10px;flex-wrap:wrap">'
               + "".join(f'<span class="leg-item"><span class="sw" style="background:{cor}"></span>'
                         f'{nome}</span>' for _, cor, nome in series)
               + '</div>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" style="display:block">'
            + "".join(barras) + "</svg>" + legenda)


def _projetos_por_ano(p: dict) -> list[tuple[str, int, int, int]]:
    """Por ano: (ações, participações da pessoa, pessoas impactadas).

    Tudo por AÇÃO, batendo com as tabelas e os tiles da página:
    - ações         = ações distintas que coordenou ou participou.
    - participações = 1 por ação coordenada + 1 por ação em que foi equipe
                      (mesma contagem das duas tabelas: coordenadas + em equipe).
    - impacto       = público-alvo distinto: da ação inteira quando coordenou;
                      das atividades em que atuou quando foi da equipe.
    """
    from collections import Counter as _C
    acoes, parts, impacto = _C(), _C(), _C()
    vistos: set = set()
    coord_ids = {r["acao_id"] for r in p["coordena"]}
    # impacto de equipe por ação = soma do público das atividades em que atuou
    imp_eq: dict = {}
    for at in p.get("atividades", []):
        imp_eq[at.get("acao_id")] = imp_eq.get(at.get("acao_id"), 0) + at.get("pub", 0)
    for r in p["coordena"] + p["participa"]:
        chave = (r["ano"], r["acao_id"])
        if r["ano"] and chave not in vistos:
            vistos.add(chave)
            acoes[r["ano"]] += 1
    for r in p["coordena"]:                 # coordenou: 1 participação; impacto = público da ação
        if r["ano"]:
            parts[r["ano"]] += 1
            impacto[r["ano"]] += r.get("pub", 0)
    for r in p["participa"]:                 # equipe: 1 participação por ação
        if r["ano"]:
            parts[r["ano"]] += 1
            if r["acao_id"] not in coord_ids:   # evita duplicar quando também coordena
                impacto[r["ano"]] += imp_eq.get(r["acao_id"], 0)
    anos = sorted(set(acoes) | set(parts))
    return [(a, acoes[a], parts[a], impacto[a]) for a in anos]


def _pagina_extensionista(p: dict, resumo: str | None, colabs: list) -> str:
    tiles = (f'<div class="tiles">{_tile(len(p["coordena"]), "Ações coordenadas")}'
             f'{_tile(len(p["participa"]), "Participações em equipe")}'
             f'{_tile(len(colabs), "Colaboradores")}'
             f'{_tile(escape("–".join(p["anos"][:1] + p["anos"][-1:])) if p["anos"] else "—", "Período ativo")}</div>')
    bio = (f'<div class="resumo">{escape(resumo)}<br>'
           f'<small style="color:var(--muted)">Resumo gerado por IA (Mistral) a partir dos '
           f'registros do SRC.</small></div>' if resumo else "")
    blocos = [tiles, bio]
    # projetos de extensão por ano (barras verticais)
    ppa = _projetos_por_ano(p)
    if ppa:
        blocos.append(f'<div class="card" style="margin-top:14px"><h2>Ações, participações e impacto por ano</h2>'
                      f'<p class="sec-desc">Por ano: <b>ações</b> (coordenadas ou em equipe), '
                      f'<b>participações</b> da pessoa (1 por ação coordenada + 1 por ação em equipe — '
                      f'igual à soma das duas tabelas abaixo) e <b>pessoas impactadas</b> pelas '
                      f'participações dela (público-alvo da ação quando coordenou; das atividades quando '
                      f'foi da equipe). Escalas independentes por série.</p>'
                      f'{_barras_v2(ppa)}</div>')
    # impacto por ação da equipe (soma do público das atividades em que atuou)
    # e nomes das atividades em que atuou, por ação
    imp_eq: dict = {}
    ativ_por_acao: dict = {}
    for at in p.get("atividades", []):
        aid = at.get("acao_id")
        imp_eq[aid] = imp_eq.get(aid, 0) + at.get("pub", 0)
        nm = (at.get("atividade") or "").strip()
        if nm:
            ativ_por_acao.setdefault(aid, []).append(nm)
    coord_ids = {r["acao_id"] for r in p["coordena"]}
    if p["coordena"]:
        rows = "".join(
            f'<tr><td><a class="lk" href="../acoes/{r["acao_id"]}.html">{escape(r["titulo"][:75])}</a></td>'
            f'<td>{escape(r["tipo"])}</td><td>{escape(r["ano"])}</td>'
            f'<td>{r["n"]}</td><td>{r.get("pub", 0)}</td></tr>'
            for r in sorted(p["coordena"], key=lambda x: x["ano"], reverse=True))
        blocos.append(f'<div class="card" style="margin-top:14px"><h2>Ações coordenadas</h2>'
                      f'<p class="sec-desc"><b>Participações da ação</b> = público-alvo + equipe (total '
                      f'registrado). <b>Pessoas impactadas</b> = público-alvo distinto (o que entra no '
                      f'gráfico acima).</p>'
                      f'<table class="tb"><tr><th>Ação</th><th>Tipo</th><th>Ano</th>'
                      f'<th>Participações da ação</th><th>Pessoas impactadas</th></tr>{rows}</table></div>')
    if p["participa"]:
        def _ativs(aid):
            nomes = sorted(set(ativ_por_acao.get(aid, [])))
            if not nomes:
                return "—"
            return "<br>".join(escape(x) for x in nomes)
        rows = "".join(
            f'<tr><td><a class="lk" href="../acoes/{r["acao_id"]}.html">{escape(r["titulo"][:70])}</a></td>'
            f'<td>{_ativs(r["acao_id"])}</td>'
            f'<td>{escape(", ".join(r["funcoes"]))}</td><td>{escape(r["ano"])}</td>'
            f'<td>{"—" if r["acao_id"] in coord_ids else imp_eq.get(r["acao_id"], 0)}</td></tr>'
            for r in sorted(p["participa"], key=lambda x: x["ano"], reverse=True))
        blocos.append(f'<div class="card" style="margin-top:14px"><h2>Participações em equipe</h2>'
                      f'<p class="sec-desc"><b>Atividade</b> = atividade(s) da ação em que a pessoa '
                      f'atuou. <b>Pessoas impactadas</b> = público-alvo distinto dessas atividades '
                      f'("—" quando também é coordenador(a), já contado acima).</p>'
                      f'<table class="tb"><tr><th>Ação</th><th>Atividade</th><th>Função</th>'
                      f'<th>Ano</th><th>Pessoas impactadas</th></tr>{rows}</table></div>')
    # rede pessoal: com quem trabalhou (grafo ego + tabela)
    if colabs:
        crows = "".join(
            f'<tr><td>'
            + (f'<a class="lk" href="{cs}.html">{escape(cn)}</a>' if cs else escape(cn))
            + f'</td><td>{cnt} ação(ões) em comum</td></tr>'
            for cn, cs, cnt in colabs[:30])
        blocos.append(
            f'<div class="card" style="margin-top:14px"><h2>Trabalhou com ({len(colabs)})</h2>'
            f'<p class="sec-desc">Colaboradores que atuaram na coordenação/equipe das mesmas ações.</p>'
            f'{_ego_grafo(p["nome"], colabs)}'
            f'<table class="tb" style="margin-top:12px"><tr><th>Pessoa</th><th>Em comum</th></tr>'
            f'{crows}</table></div>')
    blocos.append('<div class="pii">Página gerada a partir dos registros públicos de execução '
                  'do SRC (crédito de equipe). Não contém CPF, e-mail ou dados de alunos atendidos.</div>')
    papel = "Coordenador(a) e equipe" if (p["coordena"] and p["participa"]) else (
        "Coordenador(a)" if p["coordena"] else "Equipe de execução")
    return _doc(p["nome"], "../", "extensionistas/index.html", "Extensionistas",
                p["nome"], f"Extensionista — {papel} · Campus Serra", "".join(blocos))


def _pagina_extensionistas_index(pessoas: list[dict]) -> str:
    idx = [{"s": p["slug"], "n": p["nome"], "c": len(p["coordena"]),
            "e": len(p["participa"])} for p in pessoas]
    dados = json.dumps(idx, ensure_ascii=False)
    script = """
<script>
const IDX=__DADOS__;
const norm=s=>s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
IDX.forEach(p=>p.nn=norm(p.n));
const inp=document.getElementById('q'),out=document.getElementById('res');
function render(q){
  const t=norm(q.trim());
  const hits=IDX.filter(p=>!t||p.nn.includes(t));
  let h=`<div class="card" style="margin-top:14px"><p class="sec-desc">${hits.length} extensionista(s)</p><table class="tb"><tr><th>Nome</th><th>Coordena</th><th>Equipe</th></tr>`;
  for(const p of hits.slice(0,400))
    h+=`<tr><td><a class="lk" href="${p.s}.html">${p.n}</a></td><td>${p.c||'—'}</td><td>${p.e||'—'}</td></tr>`;
  out.innerHTML=h+'</table></div>';
}
inp.addEventListener('input',e=>render(e.target.value));render('');
</script>""".replace("__DADOS__", dados)
    n_coord = sum(1 for p in pessoas if p["coordena"])
    conteudo = (f'<div class="tiles">{_tile(len(pessoas), "Extensionistas")}'
                f'{_tile(n_coord, "Coordenadores(as)")}'
                f'{_tile(sum(1 for p in pessoas if p["participa"]), "Na equipe de execução")}</div>'
                f'<input class="busca" id="q" type="search" placeholder="Filtrar por nome...">'
                f'<div id="res"></div>{script}')
    return _doc("Extensionistas — Campus Serra", "../", "extensionistas/index.html",
                "Extensionistas", "Extensionistas do Campus Serra",
                "Quem coordenou ou atuou na equipe de execução de ações de Extensão — "
                "clique no nome para ver a trajetória", conteudo)


# ------------------------------------------------------------- jornada do formado
def _pagina_jornada(cons: dict, formandos_dir: str) -> str:
    a = agregar_jornada(cons, formandos_dir)
    pct = f'{a["pct_ext"]:.0f}% dos formados'
    ie = f'{a["med_ing_ext"]:.1f} anos'
    ef = f'{a["med_ext_form"]:.1f} anos'
    tiles = "".join([
        '<div class="tiles">',
        _tiler(a["n_formados"], "Formados analisados"),
        _tiler(a["com_ext"], "Fizeram extensão", pct),
        _tiler(ie, "Ingresso → 1ª extensão", "mediana"),
        _tiler(ef, "1ª extensão → formatura", "mediana"),
        _tiler(a["apos_formar"], "Voltaram após formar", "vínculo de egresso"),
        "</div>"])
    secoes = [
        _secao("Linha do tempo média", svg_timeline(a),
               "Percurso típico do formado: do ingresso à formatura, com a 1ª extensão no meio.",
               explica="Linha do tempo em escala pelas medianas: o ingresso (matrícula) na "
               "esquerda, a formatura na direita (curso ~4 anos) e o ponto médio em que os "
               "formados registram a primeira participação em extensão. O trecho colorido é o "
               "tempo típico até o primeiro contato com a extensão."),
        _secao("Funil da jornada", svg_funil(a),
               "De todos os formados até os que seguem ativos após formar.",
               explica="Afunilamento: quantos dos formados chegaram a participar de extensão e, "
               "desses, quantos continuaram ativos como egressos (participação após a formatura). "
               "Mede alcance e retenção de longo prazo da extensão junto aos formados."),
        _secao("Quando, na trajetória do curso, acontece a 1ª extensão", svg_curva_fase(a),
               "Densidade da primeira participação ao longo de 0% (ingresso) → 100% (formatura).",
               explica="Distribui a primeira extensão pela posição relativa no curso (decis de "
               "0% a 100% do período ingresso→formatura). Picos no começo indicam calouros "
               "engajados; picos no fim indicam envolvimento tardio (ex.: TCC/estágio). Considera "
               "só participações durante o curso — egressos entram no funil acima."),
        _secao("Quando o aluno entra na extensão (anos após ingresso)", _barras(a["dist_ing_ext"]),
               f'Duração mediana do curso (ingresso→formatura): {a["med_dur"]:.1f} anos.',
               explica="Para cada formado que fez extensão, quantos anos depois de INGRESSAR no "
               "curso (lido da matrícula) ele registra a primeira participação em ação de "
               "Extensão. Distribuição bimodal (calouros vs. veteranos) aparece aqui."),
        _secao("Adesão à extensão por curso", _barras(a["por_curso"], unidade="%"),
               "% de formados de cada curso que participaram de Extensão."),
    ]
    return _doc("Jornada do formado — Campus Serra", "", "jornada.html", "Jornada",
                "Jornada do formado na extensão",
                "Do ingresso (matrícula) à formatura: quando os formados se envolveram com a "
                "extensão. Cruzamento por nome — ressalvas de homônimo/semestre aplicam.",
                tiles + "".join(secoes))


# ------------------------------------------------------------- orquestração
def gerar_site(
    consolidado_json: str | Path = "data/serra_consolidado.json",
    out_dir: str | Path = "docs",
    formandos_dir: str | Path = "data/formandos",
) -> dict:
    """Gera as páginas do mini-site em torno do painel (que fica em index.html)."""
    cons = json.loads(Path(consolidado_json).read_text(encoding="utf-8"))
    out = Path(out_dir)
    (out / "acoes").mkdir(parents=True, exist_ok=True)

    # mapa nome->slug dos extensionistas (para linkar nomes em todo o site)
    from .extensionistas import _norm, coletar_extensionistas
    pessoas = coletar_extensionistas(cons)
    slugs = {_norm(p["nome"]): p["slug"] for p in pessoas}

    n = n_ativ = 0
    (out / "atividades").mkdir(exist_ok=True)
    for a in cons["acoes"]:
        (out / "acoes" / f"{a.get('acao_id')}.html").write_text(_pagina_acao(a, slugs), encoding="utf-8")
        n += 1
        for aid, m in _agrupar_atividades(a).items():
            if aid and aid != "?":
                (out / "atividades" / f"{aid}.html").write_text(
                    _pagina_atividade(a, aid, m, slugs), encoding="utf-8")
                n_ativ += 1
    (out / "acoes" / "index.html").write_text(_pagina_geral(cons, slugs), encoding="utf-8")
    busca = _pagina_busca(cons, slugs, pessoas)
    (out / "index.html").write_text(busca, encoding="utf-8")   # busca é a home
    (out / "busca.html").write_text(busca, encoding="utf-8")   # compat links antigos
    (out / "sem-participacao.html").write_text(_pagina_sem_participacao(cons, slugs), encoding="utf-8")
    (out / "pendencias-relatorio.html").write_text(_pagina_pendencias(cons, slugs), encoding="utf-8")
    try:
        (out / "jornada.html").write_text(_pagina_jornada(cons, str(formandos_dir)), encoding="utf-8")
    except Exception as e:
        print("jornada:", e)

    # extensionistas (resumos IA vêm do cache gerado por gerar_resumos)
    from .extensionistas import _CACHE_PADRAO, coautoria
    resumos = {}
    if Path(_CACHE_PADRAO).exists():
        resumos = json.loads(Path(_CACHE_PADRAO).read_text(encoding="utf-8"))
    co = coautoria(cons)   # nome_norm -> Counter(nome_colab -> nº ações)
    (out / "extensionistas").mkdir(exist_ok=True)
    for p in pessoas:
        colabs = [(cn, slugs.get(_norm(cn)), cnt)
                  for cn, cnt in co.get(_norm(p["nome"]), Counter()).most_common()]
        (out / "extensionistas" / f"{p['slug']}.html").write_text(
            _pagina_extensionista(p, resumos.get(p["slug"]), colabs), encoding="utf-8")
    (out / "extensionistas" / "index.html").write_text(
        _pagina_extensionistas_index(pessoas), encoding="utf-8")
    stats = {"paginas_acao": n, "atividades": n_ativ,
             "extensionistas": len(pessoas), "out": str(out)}
    (out / "dados-abertos.html").write_text(_pagina_dados(out, stats), encoding="utf-8")
    return stats


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="src-etl-site",
                                 description="Gera o mini-site (páginas por ação, busca, pendências).")
    ap.add_argument("--consolidado", default="data/serra_consolidado.json")
    ap.add_argument("--out", default="docs")
    args = ap.parse_args(argv)
    s = gerar_site(args.consolidado, args.out)
    print(f"site gerado em {s['out']}: {s['paginas_acao']} páginas de ação + geral/busca/listas")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
