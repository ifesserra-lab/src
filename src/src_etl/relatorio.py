"""Gera um relatório analítico HTML (self-contained) dos dados extraídos.

Lê:
  - data/serra/acao_*.json        (ações — etapa pública)
  - data/participacoes/*.json     (participações — etapa autenticada, opcional)

Agrega (sem expor dados pessoais: sem nomes/CPF individuais) e emite um HTML
único, com CSS/SVG inline, tema claro/escuro. Uso:

    from src_etl.relatorio import gerar_relatorio
    gerar_relatorio("data/serra", "data/participacoes", "relatorio.html")

CLI:  src-etl-report --acoes data/serra --part data/participacoes --out relatorio.html
"""

from __future__ import annotations

import glob
import json
import math
from collections import Counter
from html import escape
from pathlib import Path

# paleta categórica validada (dataviz) — ordem fixa
_CAT = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]


# --------------------------------------------------------------------- agregação
def _carregar_acoes(acoes_dir: str | Path) -> list[dict]:
    out = []
    for f in glob.glob(str(Path(acoes_dir) / "acao_*.json")):
        out.append(json.loads(Path(f).read_text(encoding="utf-8")))
    return out


def _carregar_participacoes(part_dir: str | Path) -> list[dict]:
    out = []
    p = Path(part_dir)
    if p.exists():
        for f in glob.glob(str(p / "participacoes_*.json")):
            out.append(json.loads(Path(f).read_text(encoding="utf-8")))
    return out


def _ano(data_cadastro: str | None) -> str:
    if data_cadastro and "/" in data_cadastro:
        return data_cadastro.split("/")[-1]
    return "?"


def agregar(acoes: list[dict], parts: list[dict]) -> dict:
    natureza = Counter(a.get("Natureza") or "—" for a in acoes)
    tipo = Counter(a.get("Tipo ação") or "—" for a in acoes)
    fomento = Counter(a.get("Fomento") or "—" for a in acoes)
    anos = Counter(_ano(a.get("Data de cadastro")) for a in acoes)
    def _cat(a: dict, chave: str) -> tuple[str, bool]:
        """Valor original; se vazio, usa o inferido (marcado como inferido)."""
        v = (a.get(chave) or "").strip()
        if v:
            return v, False
        inf = (a.get(f"{chave} (inferida)") or "").strip()
        if inf:
            return inf, True
        return "(não informado)", False

    ga_vals = [_cat(a, "Grande área conhecimento") for a in acoes]
    at_vals = [_cat(a, "Área temática principal") for a in acoes]
    grande_area = Counter(v for v, _ in ga_vals)
    area_tematica = Counter(v for v, _ in at_vals)
    n_ga_inferida = sum(1 for _, inf in ga_vals if inf)
    n_at_inferida = sum(1 for _, inf in at_vals if inf)
    relatorio = Counter((a.get("Relatório aprovado") or "—").strip() or "—" for a in acoes)

    # participações
    titulo_por_proc = {a.get("Processo nº"): (a.get("Título ação") or "") for a in acoes}
    total_atividades = sum(p.get("total_atividades", 0) for p in parts)
    total_publico = sum(p.get("total_publico_alvo", 0) for p in parts)
    total_equipe = sum(p.get("total_equipe", 0) for p in parts)

    situacao = Counter()
    certificado = Counter()
    funcao = Counter()
    publico_por_acao: list[tuple[str, int]] = []
    equipe_por_acao_vals: list[int] = []

    for p in parts:
        titulo = titulo_por_proc.get(p.get("processo"), p.get("processo", ""))
        npa = 0
        for ativ in p.get("atividades", []):
            for pessoa in ativ.get("publico_alvo", []):
                npa += 1
                situacao[(pessoa.get("Situação") or "—").strip() or "—"] += 1
                cert = (pessoa.get("Certificado") or "").strip().lower()
                certificado["Emitido" if cert and cert not in ("não", "nao", "-", "") else "Não emitido"] += 1
            for membro in ativ.get("equipe_execucao", []):
                funcao[(membro.get("Função") or "—").strip() or "—"] += 1
        if npa:
            publico_por_acao.append((titulo, npa))
        equipe_por_acao_vals.append(p.get("total_equipe", 0))

    # ações SEM participações (público=0 E equipe=0), entre as coletadas
    part_por_proc = {p.get("processo"): p for p in parts}
    sem_participacao = []
    nao_coletados = []
    coord_sem = Counter()       # ações sem participação por coordenador
    coord_com = Counter()       # ações COM participação por coordenador
    coord_total = Counter((a.get("Coordenador(a)") or "—").strip() or "—" for a in acoes)
    for a in acoes:
        proc = a.get("Processo nº")
        p = part_por_proc.get(proc)
        titulo_a = a.get("Título ação") or proc or "—"
        tipo_a = a.get("Tipo ação") or ""
        nome_c = (a.get("Coordenador(a)") or "—").strip() or "—"
        if p is None:
            nao_coletados.append((titulo_a, proc, tipo_a))
        elif p.get("total_publico_alvo", 0) == 0 and p.get("total_equipe", 0) == 0:
            sem_participacao.append((titulo_a, proc, tipo_a))
            coord_sem[nome_c] += 1
        else:
            coord_com[nome_c] += 1

    # ranking por ações sem participação (com proporção sobre o total do coordenador)
    coord_sem_rank = [(nome, n, coord_total[nome]) for nome, n in coord_sem.most_common(12)]
    # Top coordenadores: conta só ações COM participação; sem participações -> usa total
    coordenadores = coord_com if parts else coord_total

    top_publico = sorted(publico_por_acao, key=lambda x: -x[1])[:10]
    media_equipe = (sum(equipe_por_acao_vals) / len(equipe_por_acao_vals)) if equipe_por_acao_vals else 0
    taxa_cert = (certificado.get("Emitido", 0) / total_publico * 100) if total_publico else 0

    return {
        "n_acoes": len(acoes),
        "n_processos_part": len(parts),
        "total_atividades": total_atividades,
        "total_publico": total_publico,
        "total_equipe": total_equipe,
        "media_equipe": media_equipe,
        "taxa_cert": taxa_cert,
        "natureza": natureza.most_common(),
        "tipo": tipo.most_common(),
        "fomento": fomento.most_common(8),
        "anos": sorted(anos.items()),
        "coordenadores": coordenadores.most_common(10),
        "grande_area": grande_area.most_common(6),
        "area_tematica": area_tematica.most_common(6),
        "n_ga_inferida": n_ga_inferida,
        "n_at_inferida": n_at_inferida,
        "relatorio": relatorio.most_common(),
        "situacao": situacao.most_common(),
        "certificado": certificado.most_common(),
        "funcao": funcao.most_common(8),
        "top_publico": top_publico,
        "sem_participacao": sem_participacao,
        "nao_coletados": nao_coletados,
        "coord_sem_rank": coord_sem_rank,
    }


# ------------------------------------------------------------------------ SVG
def _barras(dados: list[tuple[str, int]], *, unidade: str = "") -> str:
    """Barras horizontais (série única, hue azul, rótulo de valor direto)."""
    if not dados:
        return '<p class="vazio">Sem dados ainda.</p>'
    maxv = max(v for _, v in dados) or 1
    lh, bw, lblw = 30, 320, 210
    h = len(dados) * lh + 8
    linhas = []
    for i, (nome, v) in enumerate(dados):
        y = i * lh + 4
        w = max(3, round(v / maxv * bw))
        linhas.append(
            f'<text x="{lblw-8}" y="{y+16}" text-anchor="end" class="lbl">{escape(str(nome)[:28])}</text>'
            f'<rect x="{lblw}" y="{y+5}" width="{w}" height="16" rx="4" fill="var(--series-1)"/>'
            f'<text x="{lblw+w+6}" y="{y+16}" class="val">{v}{unidade}</text>'
        )
    return (f'<svg viewBox="0 0 {lblw+bw+60} {h}" width="100%" role="img">'
            + "".join(linhas) + "</svg>")


def _donut(dados: list[tuple[str, int]]) -> str:
    """Donut categórico (ordem fixa da paleta) + legenda."""
    if not dados:
        return '<p class="vazio">Sem dados ainda.</p>'
    total = sum(v for _, v in dados) or 1
    cx = cy = 90
    r, rin = 80, 48
    ang = -math.pi / 2
    arcos, leg = [], []
    for i, (nome, v) in enumerate(dados):
        cor = _CAT[i % len(_CAT)]
        frac = v / total
        a2 = ang + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
        x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
        xi1, yi1 = cx + rin * math.cos(a2), cy + rin * math.sin(a2)
        xi2, yi2 = cx + rin * math.cos(ang), cy + rin * math.sin(ang)
        arcos.append(
            f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f} '
            f'L{xi1:.1f},{yi1:.1f} A{rin},{rin} 0 {large} 0 {xi2:.1f},{yi2:.1f} Z" '
            f'fill="{cor}" stroke="var(--surface-1)" stroke-width="2"><title>{escape(str(nome))}: {v} ({frac*100:.0f}%)</title></path>'
        )
        pct = f"{frac*100:.0f}%"
        leg.append(
            f'<div class="leg-item"><span class="sw" style="background:{cor}"></span>'
            f'<span class="leg-nome">{escape(str(nome)[:26])}</span>'
            f'<span class="leg-val">{v} · {pct}</span></div>'
        )
        ang = a2
    svg = (f'<svg viewBox="0 0 180 180" width="180" height="180" role="img">{"".join(arcos)}'
           f'<text x="{cx}" y="{cy-4}" text-anchor="middle" class="donut-num">{total}</text>'
           f'<text x="{cx}" y="{cy+14}" text-anchor="middle" class="donut-cap">total</text></svg>')
    return f'<div class="donut-wrap">{svg}<div class="leg">{"".join(leg)}</div></div>'


def _lista_acoes(itens: list[tuple[str, str, str]]) -> str:
    """Lista rolável de ações (título · tipo · processo)."""
    if not itens:
        return '<p class="vazio">Nenhuma — todas as ações têm participações.</p>'
    linhas = "".join(
        f'<div class="li"><span class="li-tit">{escape(str(t)[:70])}</span>'
        f'<span class="li-tipo">{escape(str(tp))}</span>'
        f'<span class="li-proc">{escape(str(pr) or "—")}</span></div>'
        for t, pr, tp in itens
    )
    return f'<div class="lista">{linhas}</div>'


def _ranking_coord(itens: list[tuple[str, int, int]]) -> str:
    """Ranking de coordenadores: barra pelo nº sem participação + proporção."""
    if not itens:
        return '<p class="vazio">Sem dados ainda.</p>'
    maxv = max(n for _, n, _ in itens) or 1
    bw, lblw = 240, 250
    lh = 30
    h = len(itens) * lh + 8
    linhas = []
    for i, (nome, n, tot) in enumerate(itens):
        y = i * lh + 4
        w = max(3, round(n / maxv * bw))
        pct = round(n / tot * 100) if tot else 0
        linhas.append(
            f'<text x="{lblw-8}" y="{y+16}" text-anchor="end" class="lbl">{escape(str(nome)[:30])}</text>'
            f'<rect x="{lblw}" y="{y+5}" width="{w}" height="16" rx="4" fill="var(--series-1)"/>'
            f'<text x="{lblw+w+6}" y="{y+16}" class="val">{n} de {tot} ({pct}%)</text>'
        )
    return (f'<svg viewBox="0 0 {lblw+bw+110} {h}" width="100%" role="img">'
            + "".join(linhas) + "</svg>")


def _tile(valor, rotulo: str, sub: str = "") -> str:
    subhtml = f'<div class="tile-sub">{escape(sub)}</div>' if sub else ""
    return (f'<div class="tile"><div class="tile-val">{valor}</div>'
            f'<div class="tile-lbl">{escape(rotulo)}</div>{subhtml}</div>')


def _secao(titulo: str, corpo: str, desc: str = "") -> str:
    d = f'<p class="sec-desc">{escape(desc)}</p>' if desc else ""
    return f'<section><h2>{escape(titulo)}</h2>{d}<div class="card">{corpo}</div></section>'


# ------------------------------------------------------------------------ HTML
_CSS = """
:root{color-scheme:light;--plane:#f9f9f7;--surface-1:#fcfcfb;--text-primary:#0b0b0b;
--text-secondary:#52514e;--muted:#898781;--grid:#e1e0d9;--border:rgba(11,11,11,.10);
--series-1:#2a78d6}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){color-scheme:dark;
--plane:#0d0d0d;--surface-1:#1a1a19;--text-primary:#fff;--text-secondary:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--border:rgba(255,255,255,.10);--series-1:#3987e5}}
:root[data-theme=dark]{color-scheme:dark;--plane:#0d0d0d;--surface-1:#1a1a19;
--text-primary:#fff;--text-secondary:#c3c2b7;--grid:#2c2c2a;--border:rgba(255,255,255,.10);
--series-1:#3987e5}
*{box-sizing:border-box}body{margin:0;background:var(--plane);color:var(--text-primary);
font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.45}
.wrap{max-width:1000px;margin:0 auto;padding:32px 20px 64px}
header h1{margin:0 0 4px;font-size:1.6rem}header .sub{color:var(--text-secondary);margin:0 0 8px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0 8px}
.tile{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:16px}
.tile-val{font-size:1.9rem;font-weight:700;letter-spacing:-.02em}
.tile-lbl{color:var(--text-secondary);font-size:.85rem;margin-top:2px}
.tile-sub{color:var(--muted);font-size:.75rem;margin-top:4px}
section{margin-top:28px}h2{font-size:1.1rem;margin:0 0 2px}
.sec-desc{color:var(--text-secondary);font-size:.85rem;margin:0 0 10px}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:18px;overflow-x:auto}
.lbl{fill:var(--text-secondary);font-size:12px}.val{fill:var(--text-primary);font-size:12px;font-weight:600}
.vazio{color:var(--muted);margin:0;font-size:.9rem}
.donut-wrap{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.donut-num{fill:var(--text-primary);font-size:26px;font-weight:700}
.donut-cap{fill:var(--muted);font-size:11px}
.leg{display:flex;flex-direction:column;gap:6px;min-width:220px}
.leg-item{display:flex;align-items:center;gap:8px;font-size:.85rem}
.sw{width:12px;height:12px;border-radius:3px;flex:none}
.leg-nome{flex:1}.leg-val{color:var(--text-secondary);font-variant-numeric:tabular-nums}
footer{margin-top:36px;color:var(--muted);font-size:.78rem;border-top:1px solid var(--border);padding-top:12px}
.pii{background:color-mix(in srgb,var(--series-1) 8%,transparent);border:1px solid var(--border);
border-radius:10px;padding:10px 14px;font-size:.82rem;color:var(--text-secondary);margin-top:12px}
.lista{max-height:340px;overflow-y:auto;display:flex;flex-direction:column;gap:1px}
.li{display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:center;
padding:7px 4px;border-bottom:1px solid var(--grid);font-size:.85rem}
.li-tit{color:var(--text-primary)}
.li-tipo{color:var(--muted);font-size:.75rem;border:1px solid var(--border);border-radius:20px;padding:1px 8px}
.li-proc{color:var(--text-secondary);font-variant-numeric:tabular-nums;font-size:.8rem}
"""


def gerar_relatorio(
    acoes_dir: str | Path = "data/serra",
    part_dir: str | Path = "data/participacoes",
    out_html: str | Path = "relatorio.html",
    *,
    titulo: str = "SRC/Ifes — Campus Serra",
) -> Path:
    acoes = _carregar_acoes(acoes_dir)
    parts = _carregar_participacoes(part_dir)
    a = agregar(acoes, parts)

    tiles = "".join([
        _tile(a["n_acoes"], "Ações"),
        _tile(a["total_atividades"] or "—", "Atividades", f'{a["n_processos_part"]} processos'),
        _tile(a["total_publico"] or "—", "Alunos atendidos"),
        _tile(a["total_equipe"] or "—", "Equipe executora", f'média {a["media_equipe"]:.1f}/ação'),
        _tile(f'{a["taxa_cert"]:.0f}%' if a["total_publico"] else "—", "Taxa de certificação"),
    ])

    # seções de ações (sempre)
    secoes = [
        _secao("Ações por natureza", _barras(a["natureza"]),
               "Distribuição das ações por natureza acadêmica."),
        _secao("Ações por tipo", _donut(a["tipo"]),
               "Programa, Projeto, Curso, Evento e demais tipos."),
        _secao("Fomento (top 8)", _barras(a["fomento"]),
               "Fonte de fomento vinculada à ação."),
        _secao("Ações por ano de cadastro", _barras(a["anos"]),
               "Volume de ações cadastradas por ano."),
        _secao("Top 10 coordenadores por nº de ações", _barras(a["coordenadores"]),
               "Proponentes mais recorrentes — contando apenas ações com participação registrada."),
        _secao("Grande área do conhecimento", _donut(a["grande_area"]),
               f'{a["n_ga_inferida"]} categorias inferidas por IA (Mistral) a partir do resumo.'),
        _secao("Área temática principal", _donut(a["area_tematica"]),
               f'{a["n_at_inferida"]} categorias inferidas por IA (Mistral) a partir do resumo.'),
        _secao("Relatório aprovado", _donut(a["relatorio"]),
               "Ações com relatório final aprovado."),
    ]
    # seções de participação (só quando há dados coletados)
    if a["n_processos_part"]:
        n_sem = len(a["sem_participacao"])
        secoes += [
            _secao("Top 10 ações por alunos atendidos", _barras(a["top_publico"]),
                   "Ações com maior público-alvo (participações)."),
            _secao("Situação dos participantes", _donut(a["situacao"]),
                   "Situação registrada do público-alvo."),
            _secao("Certificação do público-alvo", _donut(a["certificado"])),
            _secao("Equipe executora por função (top 8)", _barras(a["funcao"])),
            _secao(f"Ações sem participações ({n_sem})", _lista_acoes(a["sem_participacao"]),
                   "Ações coletadas com público-alvo = 0 e equipe = 0 registrados."),
            _secao("Coordenadores com ações sem participação",
                   _ranking_coord(a["coord_sem_rank"]),
                   "Nº de ações sem participação por coordenador(a) e proporção do total dele(a)."),
        ]
        if a["nao_coletados"]:
            secoes.append(_secao(
                f"Ações não coletadas ({len(a['nao_coletados'])})",
                _lista_acoes(a["nao_coletados"]),
                "Processo cujo detalhamento de participações falhou na extração."))

    html = f"""<div class="wrap">
<header>
  <h1>{escape(titulo)}</h1>
  <p class="sub">Relatório analítico — dados extraídos do SRC/Ifes</p>
</header>
<div class="tiles">{tiles}</div>
{''.join(secoes)}
<div class="pii">Relatório <b>agregado</b>: não contém nomes, CPF ou e-mail individuais.
Dados pessoais permanecem apenas nos arquivos locais de participações.</div>
<footer>Gerado por src-etl · {a['n_acoes']} ações · {a['n_processos_part']} processos com participações.</footer>
</div>"""

    doc = (f"<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{escape(titulo)} — Relatório</title><style>{_CSS}</style></head>"
           f"<body>{html}</body></html>")

    out = Path(out_html)
    out.write_text(doc, encoding="utf-8")
    return out


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="src-etl-report",
                                 description="Gera relatório analítico HTML (agregado).")
    ap.add_argument("--acoes", default="data/serra", help="Diretório das ações")
    ap.add_argument("--part", default="data/participacoes", help="Diretório das participações")
    ap.add_argument("--out", default="relatorio.html", help="Arquivo HTML de saída")
    ap.add_argument("--titulo", default="SRC/Ifes — Campus Serra")
    args = ap.parse_args(argv)
    p = gerar_relatorio(args.acoes, args.part, args.out, titulo=args.titulo)
    print(f"Relatório gerado: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
