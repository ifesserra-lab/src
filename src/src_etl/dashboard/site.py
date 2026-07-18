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
from .relatorio import _barras, _donut, _tile as _tiler, _secao
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
.badge{display:inline-block;border:1px solid var(--grid);border-radius:6px;padding:3px 10px;
font-size:11.5px;font-weight:500;color:var(--text-secondary);white-space:nowrap;
background:var(--surface-1)}
.tl-t{fill:var(--text-primary);font-size:14px;font-weight:600}
.tl-s{fill:var(--muted);font-size:12px}
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
<div><b>Natureza / Tipo</b>{escape(a.get('Natureza') or '—')} · {escape(a.get('Tipo ação') or '—')}</div>
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
        f'<td>{escape(a.get("Tipo ação") or "—")}</td>'
        f'<td>{_link_pessoa(a.get("Coordenador(a)"), "../", slugs)}</td>'
        f'<td>{a.get("total_participacoes", 0)}</td>'
        f'<td><span class="badge">{escape((a.get("Data de cadastro") or "—")[-4:])}</span></td></tr>'
        for a in sorted(acoes, key=lambda x: -(x.get("total_participacoes") or 0)))
    tabela = (f'<div class="card" style="margin-top:16px"><table class="tb">'
              f'<tr><th>Ação</th><th>Tipo</th><th>Coordenador(a)</th>'
              f'<th>Participações</th><th>Ano</th></tr>{rows}</table></div>')

    return _doc("Ações — Campus Serra", "../", "acoes/index.html", "Ações",
                "O que foi feito — Campus Serra",
                "Resumo geral das ações de extensão e ensino registradas no SRC",
                f"{tiles}{tabela}")


# ------------------------------------------------------------- busca
def _pagina_busca(cons: dict, slugs: dict) -> str:
    """Busca por palavras-chave: título, resumo, coordenador, tipo, natureza, áreas."""
    idx = []
    for a in cons["acoes"]:
        area = (a.get("Área temática principal") or a.get("Área temática principal (inferida)") or "")
        ga = (a.get("Grande área conhecimento") or a.get("Grande área conhecimento (inferida)") or "")
        from .extensionistas import _norm as _n
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
    dados = json.dumps(idx, ensure_ascii=False)
    script = """
<script>
const IDX = __DADOS__;
const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
IDX.forEach(a => a.nb = norm(a.b));
const inp = document.getElementById('q'), out = document.getElementById('res');
function render(q){
  out.innerHTML='';
  const termos = norm(q.trim()).split(/\\s+/).filter(t=>t.length>=2);
  if(!termos.length){out.innerHTML='<p class="vazio">Digite palavras-chave: tema (robótica, inglês, saúde), coordenador(a), tipo (curso, evento), fomento, ano...</p>';return;}
  const hits = IDX.filter(a => termos.every(t => a.nb.includes(t)))
                  .sort((x,y)=>y.n-x.n);
  if(!hits.length){out.innerHTML='<p class="vazio">Nada encontrado para esses termos. Tente palavras mais gerais.</p>';return;}
  let h = `<div class="card" style="margin-top:14px"><p class="sec-desc">${hits.length} ação(ões) encontrada(s)</p><table class="tb"><tr><th>Ação</th><th>Coordenador(a)</th><th>Tipo</th><th>Ano</th><th>Participações</th></tr>`;
  for(const a of hits)
    h += `<tr><td><a class="lk" href="acoes/${a.id}.html">${a.t}</a></td><td>${a.cs?`<a class="lk" href="extensionistas/${a.cs}.html">${a.c}</a>`:a.c}</td><td>${a.tp}</td><td>${a.ano}</td><td>${a.n}</td></tr>`;
  out.innerHTML = h + '</table></div>';
}
inp.addEventListener('input', e=>render(e.target.value)); render('');
</script>""".replace("__DADOS__", dados)
    chips = "".join(f'<button data-q="{c}">{c}</button>'
                    for c in ["robótica", "inglês", "saúde", "curso 2024", "cultura", "FAPES"])
    script += """
<script>
document.querySelectorAll('.chips button').forEach(b=>b.addEventListener('click',()=>{
  const q=document.getElementById('q'); q.value=b.dataset.q;
  q.dispatchEvent(new Event('input')); q.focus();
}));
</script>"""
    conteudo = (f'<input class="busca" id="q" type="search" autofocus '
                f'placeholder="Busque por tema, coordenador(a), tipo, fomento, ano..."'
                f'><div class="chips">{chips}</div>'
                f'<div id="res"></div>{script}')
    return _doc("SRC · Campus Serra — Buscar", "", "index.html", "Buscar",
                "O que a extensão do Campus Serra já fez?",
                "Busque nas 201 ações por palavras-chave — título, resumo, coordenador(a), "
                "tipo, área temática, fomento ou processo",
                conteudo, hero=True)


# ------------------------------------------------------------- listas de gestão
def _tabela_acoes(itens: list[dict], slugs: dict, extra_col: tuple[str, str] | None = None) -> str:
    cab = "<tr><th>Ação</th><th>Tipo</th><th>Coordenador(a)</th><th>Ano</th>"
    cab += f"<th>{escape(extra_col[0])}</th></tr>" if extra_col else "</tr>"
    rows = []
    for it in itens:
        extra = f"<td>{escape(str(it.get(extra_col[1]) or '—'))}</td>" if extra_col else ""
        rows.append(
            f'<tr><td><a class="lk" href="acoes/{escape(str(it.get("acao_id")))}.html">'
            f'{escape((it.get("titulo") or "—")[:75])}</a></td>'
            f'<td>{escape(it.get("tipo") or "—")}</td>'
            f'<td>{_link_pessoa(it.get("coordenador"), "", slugs)}</td>'
            f'<td>{escape(it.get("ano") or "—")}</td>{extra}</tr>')
    return f'<div class="card" style="margin-top:16px"><table class="tb">{cab}{"".join(rows)}</table></div>'


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
    return _doc("Ações sem participações — Campus Serra", "", "sem-participacao.html",
                "Sem participações", f"Ações sem participações ({len(itens)})",
                "Ações sem nenhum público-alvo nem equipe registrados no SRC — "
                "pendência de registro a regularizar com o(a) coordenador(a)",
                _tabela_acoes(itens, slugs))


def _pagina_pendencias(cons: dict, slugs: dict) -> str:
    itens = []
    for a in cons["acoes"]:
        if (a.get("Relatório aprovado") or "").strip().lower() != "sim":
            itens.append({"acao_id": a.get("acao_id"),
                          "titulo": a.get("Título ação"),
                          "tipo": a.get("Tipo ação"),
                          "coordenador": (a.get("Coordenador(a)") or "—").strip(),
                          "ano": (a.get("Data de cadastro") or "")[-4:],
                          "ultimo": a.get("Data último relatório") or "nunca enviado"})
    itens.sort(key=lambda x: (x["coordenador"], x["ano"]))
    # ranking por coordenador
    cont = Counter(i["coordenador"] for i in itens)
    top = "".join(f'<span class="badge" style="margin:3px">{escape(n)}: {q}</span>'
                  for n, q in cont.most_common(12))
    return _doc("Pendências de relatório — Campus Serra", "", "pendencias-relatorio.html",
                "Pendências", f"Pendências de relatório ({len(itens)})",
                "Ações sem relatório final aprovado no SRC (inclui ações em andamento) — "
                "com o(a) coordenador(a) responsável",
                f'<div class="card">{top}</div>{_tabela_acoes(itens, slugs, ("Últ. relatório", "ultimo"))}')


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


def _barras_v(dados: list[tuple[str, int]]) -> str:
    """Barras VERTICAIS que preenchem a largura: x = rótulo (ano), y = quantidade."""
    if not dados:
        return '<p class="vazio">Sem dados.</p>'
    maxv = max(v for _, v in dados) or 1
    n = len(dados)
    W, top, base_h = 1000, 26, 150          # viewBox largo; escala uniforme a 100%
    H = top + base_h + 30
    slot = W / n
    bw = min(90, slot * 0.6)                # barra ocupa 60% do slot (teto 90px)
    barras = []
    for i, (rot, v) in enumerate(dados):
        cx = slot * (i + 0.5)
        bh = max(2, round(v / maxv * base_h))
        y = top + base_h - bh
        barras.append(
            f'<rect x="{cx-bw/2:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="5" fill="var(--series-1)">'
            f'<title>{escape(rot)}: {v}</title></rect>'
            f'<text x="{cx:.1f}" y="{y-7}" text-anchor="middle" class="val">{v}</text>'
            f'<text x="{cx:.1f}" y="{top+base_h+19}" text-anchor="middle" class="lbl">{escape(rot)}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" style="display:block">'
            + "".join(barras) + "</svg>")


def _projetos_por_ano(p: dict) -> list[tuple[str, int]]:
    """Nº de ações (coordenadas + equipe) por ano, distintas por ação."""
    from collections import Counter as _C
    por_ano = _C()
    vistos: set = set()
    for r in p["coordena"] + p["participa"]:
        chave = (r["ano"], r["acao_id"])
        if r["ano"] and chave not in vistos:
            vistos.add(chave)
            por_ano[r["ano"]] += 1
    return [(a, por_ano[a]) for a in sorted(por_ano)]


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
        blocos.append(f'<div class="card" style="margin-top:14px"><h2>Ações de extensão por ano</h2>'
                      f'<p class="sec-desc">Nº de ações (coordenadas ou em equipe) por ano.</p>'
                      f'{_barras_v(ppa)}</div>')
    if p["coordena"]:
        rows = "".join(
            f'<tr><td><a class="lk" href="../acoes/{r["acao_id"]}.html">{escape(r["titulo"][:75])}</a></td>'
            f'<td>{escape(r["tipo"])}</td><td>{escape(r["ano"])}</td><td>{r["n"]}</td></tr>'
            for r in sorted(p["coordena"], key=lambda x: x["ano"], reverse=True))
        blocos.append(f'<div class="card" style="margin-top:14px"><h2>Ações coordenadas</h2>'
                      f'<table class="tb"><tr><th>Ação</th><th>Tipo</th><th>Ano</th>'
                      f'<th>Participações</th></tr>{rows}</table></div>')
    if p["participa"]:
        rows = "".join(
            f'<tr><td><a class="lk" href="../acoes/{r["acao_id"]}.html">{escape(r["titulo"][:75])}</a></td>'
            f'<td>{escape(", ".join(r["funcoes"]))}</td><td>{escape(r["ano"])}</td></tr>'
            for r in sorted(p["participa"], key=lambda x: x["ano"], reverse=True))
        blocos.append(f'<div class="card" style="margin-top:14px"><h2>Participações em equipe</h2>'
                      f'<table class="tb"><tr><th>Ação</th><th>Função</th><th>Ano</th></tr>{rows}</table></div>')
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
    busca = _pagina_busca(cons, slugs)
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
    return {"paginas_acao": n, "atividades": n_ativ,
            "extensionistas": len(pessoas), "out": str(out)}


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
