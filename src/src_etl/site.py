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

from .painel import HORIZON_CSS

_EXTRA_CSS = """
.topnav{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 6px}
.topnav a{padding:9px 16px;border-radius:14px;font-weight:700;font-size:.85rem;text-decoration:none;
color:var(--text-secondary);background:var(--surface-1);border:1px solid var(--border);box-shadow:var(--shadow)}
.topnav a:hover,.topnav a.on{background:var(--series-1);color:#fff;border-color:var(--series-1)}
table.tb{width:100%;border-collapse:collapse;font-size:.85rem}
table.tb th{color:var(--text-secondary);text-align:left;padding:8px 10px;border-bottom:2px solid var(--grid);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
table.tb td{padding:8px 10px;border-bottom:1px solid var(--grid);vertical-align:top}
table.tb tr:hover td{background:color-mix(in srgb,var(--series-1) 5%,transparent)}
a.lk{color:var(--series-1);text-decoration:none;font-weight:600}
a.lk:hover{text-decoration:underline}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:14px 0}
.meta div{background:var(--surface-1);border:1px solid var(--border);border-radius:14px;padding:10px 14px;font-size:.85rem}
.meta b{display:block;color:var(--text-secondary);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px}
.resumo{background:var(--surface-1);border:1px solid var(--border);border-radius:var(--radius);padding:18px;
box-shadow:var(--shadow);color:var(--text-secondary);max-width:75ch;line-height:1.55;font-size:.92rem}
input.busca{width:100%;padding:14px 18px;border-radius:16px;border:1px solid var(--border);
background:var(--surface-1);color:var(--text-primary);font-size:1rem;box-shadow:var(--shadow);outline:none}
input.busca:focus{border-color:var(--series-1)}
.badge{display:inline-block;border:1px solid var(--border);border-radius:20px;padding:1px 10px;
font-size:.75rem;color:var(--muted);white-space:nowrap}
"""


def _doc(titulo: str, corpo: str) -> str:
    return (f"<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(titulo)}</title><style>{HORIZON_CSS}{_EXTRA_CSS}</style></head>"
            f"<body><div class='wrap'>{corpo}</div></body></html>")


def _nav(base: str, ativo: str) -> str:
    itens = [("index.html", "Painel"), ("acoes/index.html", "Ações"),
             ("busca.html", "Buscar coordenador"),
             ("sem-participacao.html", "Sem participações"),
             ("pendencias-relatorio.html", "Pendências de relatório")]
    links = "".join(
        f'<a href="{base}{href}" class="{"on" if href == ativo else ""}">{escape(rotulo)}</a>'
        for href, rotulo in itens)
    return f'<div class="topnav">{links}</div>'


def _tile(valor, rotulo, sub="") -> str:
    s = f'<div class="tile-sub">{escape(sub)}</div>' if sub else ""
    return (f'<div class="tile"><div class="tile-val">{valor}</div>'
            f'<div class="tile-lbl">{escape(rotulo)}</div>{s}</div>')


# ------------------------------------------------------------- página por ação
def _pagina_acao(a: dict) -> str:
    parts = a.get("participacoes", [])
    # agrupa por atividade
    ativm: dict[str, dict] = {}
    for p in parts:
        k = p.get("atividade_id") or "?"
        m = ativm.setdefault(k, {"num": p.get("atividade_num"), "nome": p.get("atividade"),
                                 "pub": 0, "eq": [], "aprov": 0, "cert": 0})
        if p.get("tipo", "").startswith("Público"):
            m["pub"] += 1
            if (p.get("Situação") or "").strip().upper() == "APROVADO":
                m["aprov"] += 1
            c = (p.get("Certificado") or "").strip().lower()
            if c and c not in ("não", "nao", "-"):
                m["cert"] += 1
        else:
            m["eq"].append(p)

    linhas = []
    for k, m in sorted(ativm.items(), key=lambda kv: kv[1]["num"] or ""):
        linhas.append(
            f"<tr><td>{escape(m['num'] or '—')}</td>"
            f"<td>{escape((m['nome'] or '—')[:90])}</td>"
            f"<td>{m['pub']}</td><td>{m['aprov']}</td><td>{m['cert']}</td><td>{len(m['eq'])}</td></tr>")
    tabela_ativ = (f'<div class="card" style="margin-top:14px"><table class="tb">'
                   f'<tr><th>Nº</th><th>Atividade</th><th>Público</th><th>Aprovados</th>'
                   f'<th>Certificados</th><th>Equipe</th></tr>{"".join(linhas)}</table></div>'
                   if linhas else '<div class="card"><p class="vazio">Sem atividades com participações registradas.</p></div>')

    # equipe única (nome + função), sem PII sensível
    equipe: dict[str, set] = {}
    for p in parts:
        if not p.get("tipo", "").startswith("Público"):
            equipe.setdefault((p.get("Nome") or "—").strip(), set()).add(
                (p.get("Função") or "—").strip())
    eq_rows = "".join(
        f"<tr><td>{escape(n)}</td><td>{escape(', '.join(sorted(f)))}</td></tr>"
        for n, f in sorted(equipe.items()))
    tabela_eq = (f'<div class="card" style="margin-top:14px"><table class="tb">'
                 f'<tr><th>Equipe de execução</th><th>Função(ões)</th></tr>{eq_rows}</table></div>'
                 if eq_rows else "")

    pub_total = sum(m["pub"] for m in ativm.values())
    meta = f"""<div class="meta">
<div><b>Processo</b>{escape(a.get('Processo nº') or '—')}</div>
<div><b>Coordenador(a)</b>{escape(a.get('Coordenador(a)') or '—')}</div>
<div><b>Natureza / Tipo</b>{escape(a.get('Natureza') or '—')} · {escape(a.get('Tipo ação') or '—')}</div>
<div><b>Fomento</b>{escape(a.get('Fomento') or '—')}</div>
<div><b>Cadastro</b>{escape(a.get('Data de cadastro') or '—')}</div>
<div><b>Relatório aprovado</b>{escape(a.get('Relatório aprovado') or '—')}</div>
</div>"""
    resumo = (f'<div class="resumo">{escape(a.get("Resumo") or "Sem resumo cadastrado.")}</div>')
    tiles = (f'<div class="tiles">{_tile(len(ativm), "Atividades")}'
             f'{_tile(pub_total, "Alunos atendidos", "participações de público")}'
             f'{_tile(len(equipe), "Pessoas na equipe")}</div>')

    corpo = (f"{_nav('../', '')}<header><h1>{escape(a.get('Título ação') or 'Ação')}</h1>"
             f"<p class='sub'>Ação do SRC/Ifes — Campus {escape(a.get('Campus') or a.get('campus') or '')}</p></header>"
             f"{meta}{resumo}{tiles}{tabela_ativ}{tabela_eq}"
             f"<div class='pii'>Público-alvo é mostrado apenas como contagem — nomes, CPF e "
             f"e-mail de alunos atendidos não são publicados. A equipe de execução é listada "
             f"como crédito público (sem dados pessoais).</div>")
    return _doc(a.get("Título ação") or "Ação", corpo)


# ------------------------------------------------------------- página geral
def _pagina_geral(cons: dict) -> str:
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
        f'<td>{escape((a.get("Coordenador(a)") or "—")[:35])}</td>'
        f'<td>{a.get("total_participacoes", 0)}</td>'
        f'<td><span class="badge">{escape((a.get("Data de cadastro") or "—")[-4:])}</span></td></tr>'
        for a in sorted(acoes, key=lambda x: -(x.get("total_participacoes") or 0)))
    tabela = (f'<div class="card" style="margin-top:16px"><table class="tb">'
              f'<tr><th>Ação</th><th>Tipo</th><th>Coordenador(a)</th>'
              f'<th>Participações</th><th>Ano</th></tr>{rows}</table></div>')

    corpo = (f"{_nav('../', 'acoes/index.html')}<header><h1>O que foi feito — Campus Serra</h1>"
             f"<p class='sub'>Resumo geral das ações de extensão e ensino registradas no SRC</p></header>"
             f"{tiles}{tabela}")
    return _doc("Ações — Campus Serra", corpo)


# ------------------------------------------------------------- busca
def _pagina_busca(cons: dict) -> str:
    idx: dict[str, list] = {}
    for a in cons["acoes"]:
        c = (a.get("Coordenador(a)") or "—").strip() or "—"
        idx.setdefault(c, []).append({
            "t": (a.get("Título ação") or "—")[:80], "id": a.get("acao_id"),
            "n": a.get("total_participacoes", 0),
            "ano": (a.get("Data de cadastro") or "")[-4:]})
    dados = json.dumps(idx, ensure_ascii=False)
    script = """
<script>
const IDX = __DADOS__;
const inp = document.getElementById('q'), out = document.getElementById('res');
function render(q){
  q = q.trim().toLowerCase(); out.innerHTML='';
  if(q.length<2){out.innerHTML='<p class="vazio">Digite ao menos 2 letras do nome.</p>';return;}
  const nomes = Object.keys(IDX).filter(n=>n.toLowerCase().includes(q)).sort();
  if(!nomes.length){out.innerHTML='<p class="vazio">Nenhum coordenador(a) encontrado.</p>';return;}
  for(const n of nomes){
    const acs = IDX[n];
    let h = `<div class="card" style="margin-top:14px"><h2>${n} <span class="badge">${acs.length} ação(ões)</span></h2><table class="tb">`;
    for(const a of acs.sort((x,y)=>y.n-x.n))
      h += `<tr><td><a class="lk" href="acoes/${a.id}.html">${a.t}</a></td><td>${a.ano}</td><td>${a.n} participações</td></tr>`;
    out.innerHTML += h + '</table></div>';
  }
}
inp.addEventListener('input', e=>render(e.target.value)); render('');
</script>""".replace("__DADOS__", dados)
    corpo = (f"{_nav('', 'busca.html')}<header><h1>Buscar coordenador(a)</h1>"
             f"<p class='sub'>Digite o nome para ver os projetos/ações e abrir a página de cada um</p></header>"
             f'<input class="busca" id="q" type="search" placeholder="Ex.: Emmanuel, Klauck, Moisés...">'
             f'<div id="res"></div>{script}')
    return _doc("Buscar coordenador — Campus Serra", corpo)


# ------------------------------------------------------------- listas de gestão
def _tabela_acoes(itens: list[dict], extra_col: tuple[str, str] | None = None) -> str:
    cab = "<tr><th>Ação</th><th>Tipo</th><th>Coordenador(a)</th><th>Ano</th>"
    cab += f"<th>{escape(extra_col[0])}</th></tr>" if extra_col else "</tr>"
    rows = []
    for it in itens:
        extra = f"<td>{escape(str(it.get(extra_col[1]) or '—'))}</td>" if extra_col else ""
        rows.append(
            f'<tr><td><a class="lk" href="acoes/{escape(str(it.get("acao_id")))}.html">'
            f'{escape((it.get("titulo") or "—")[:75])}</a></td>'
            f'<td>{escape(it.get("tipo") or "—")}</td>'
            f'<td>{escape(it.get("coordenador") or "—")}</td>'
            f'<td>{escape(it.get("ano") or "—")}</td>{extra}</tr>')
    return f'<div class="card" style="margin-top:16px"><table class="tb">{cab}{"".join(rows)}</table></div>'


def _pagina_sem_participacao(cons: dict) -> str:
    itens = []
    for a in cons["acoes"]:
        if a.get("total_participacoes", 0) == 0:
            itens.append({"acao_id": a.get("acao_id"),
                          "titulo": a.get("Título ação"),
                          "tipo": a.get("Tipo ação"),
                          "coordenador": (a.get("Coordenador(a)") or "—").strip(),
                          "ano": (a.get("Data de cadastro") or "")[-4:]})
    itens.sort(key=lambda x: (x["coordenador"], x["ano"]))
    corpo = (f"{_nav('', 'sem-participacao.html')}<header><h1>Ações sem participações ({len(itens)})</h1>"
             f"<p class='sub'>Ações sem nenhum público-alvo nem equipe registrados no SRC — "
             f"pendência de registro a regularizar com o(a) coordenador(a)</p></header>"
             f"{_tabela_acoes(itens)}")
    return _doc("Ações sem participações — Campus Serra", corpo)


def _pagina_pendencias(cons: dict) -> str:
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
    corpo = (f"{_nav('', 'pendencias-relatorio.html')}<header><h1>Pendências de relatório ({len(itens)})</h1>"
             f"<p class='sub'>Ações sem relatório final aprovado no SRC (inclui ações em andamento) — "
             f"com o(a) coordenador(a) responsável</p></header>"
             f'<div class="card">{top}</div>'
             f"{_tabela_acoes(itens, ('Últ. relatório', 'ultimo'))}")
    return _doc("Pendências de relatório — Campus Serra", corpo)


# ------------------------------------------------------------- orquestração
def gerar_site(
    consolidado_json: str | Path = "data/serra_consolidado.json",
    out_dir: str | Path = "docs",
) -> dict:
    """Gera as páginas do mini-site em torno do painel (que fica em index.html)."""
    cons = json.loads(Path(consolidado_json).read_text(encoding="utf-8"))
    out = Path(out_dir)
    (out / "acoes").mkdir(parents=True, exist_ok=True)

    n = 0
    for a in cons["acoes"]:
        (out / "acoes" / f"{a.get('acao_id')}.html").write_text(_pagina_acao(a), encoding="utf-8")
        n += 1
    (out / "acoes" / "index.html").write_text(_pagina_geral(cons), encoding="utf-8")
    (out / "busca.html").write_text(_pagina_busca(cons), encoding="utf-8")
    (out / "sem-participacao.html").write_text(_pagina_sem_participacao(cons), encoding="utf-8")
    (out / "pendencias-relatorio.html").write_text(_pagina_pendencias(cons), encoding="utf-8")
    return {"paginas_acao": n, "out": str(out)}


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
