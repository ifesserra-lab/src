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
    # ações ATIVAS = com alguma participação registrada (público ou equipe > 0).
    # Os gráficos de perfil (natureza, tipo, fomento, ano, áreas, relatório)
    # contam apenas ativas; as vazias aparecem nas listas de pendência.
    _pp = {p.get("processo"): p for p in parts}

    def _ativa(a: dict) -> bool:
        p = _pp.get(a.get("Processo nº"))
        if p is None:
            return not parts  # sem coleta de participações -> não filtra
        return (p.get("total_publico_alvo", 0) + p.get("total_equipe", 0)) > 0

    ativas = [a for a in acoes if _ativa(a)] if parts else list(acoes)

    natureza = Counter(a.get("Natureza") or "—" for a in ativas)
    tipo = Counter(a.get("Tipo ação") or "—" for a in ativas)
    fomento = Counter(a.get("Fomento") or "—" for a in ativas)
    anos = Counter(_ano(a.get("Data de cadastro")) for a in ativas)
    def _cat(a: dict, chave: str) -> tuple[str, bool]:
        """Valor original; se vazio, usa o inferido (marcado como inferido)."""
        v = (a.get(chave) or "").strip()
        if v:
            return v, False
        inf = (a.get(f"{chave} (inferida)") or "").strip()
        if inf:
            return inf, True
        return "(não informado)", False

    ga_vals = [_cat(a, "Grande área conhecimento") for a in ativas]
    at_vals = [_cat(a, "Área temática principal") for a in ativas]
    grande_area = Counter(v for v, _ in ga_vals)
    area_tematica = Counter(v for v, _ in at_vals)
    n_ga_inferida = sum(1 for _, inf in ga_vals if inf)
    n_at_inferida = sum(1 for _, inf in at_vals if inf)
    relatorio = Counter((a.get("Relatório aprovado") or "—").strip() or "—" for a in ativas)

    # participações — atividades contam só quando têm público ou equipe (> 0)
    titulo_por_proc = {a.get("Processo nº"): (a.get("Título ação") or "") for a in acoes}
    total_atividades = sum(
        1 for p in parts for ativ in p.get("atividades", [])
        if len(ativ.get("publico_alvo", [])) + len(ativ.get("equipe_execucao", [])) > 0)
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
        if (p.get("total_publico_alvo", 0) + p.get("total_equipe", 0)) > 0:
            equipe_por_acao_vals.append(p.get("total_equipe", 0))  # média só sobre ativas

    # ações SEM participações (público=0 E equipe=0), entre as coletadas
    part_por_proc = {p.get("processo"): p for p in parts}
    sem_participacao = []
    sem_participacao_det = []   # versão detalhada (com coordenador/ano) p/ página dedicada
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
            sem_participacao.append((titulo_a, proc, tipo_a, nome_c))
            sem_participacao_det.append({
                "titulo": titulo_a, "processo": proc, "tipo": tipo_a,
                "coordenador": nome_c, "ano": _ano(a.get("Data de cadastro")),
                "natureza": a.get("Natureza") or "—",
            })
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
        "n_acoes_ativas": len(ativas),
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
        "sem_participacao_det": sem_participacao_det,
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
    return (f'<svg viewBox="0 0 {lblw+bw+60} {h}" width="100%" role="img" '
            f'style="max-width:{lblw+bw+60}px">'
            + "".join(linhas) + "</svg>")


def _linha(dados: list[tuple[str, int]], *, unidade: str = "") -> str:
    """Gráfico de linha/área (série única) com valor em cada ponto."""
    if not dados:
        return '<p class="vazio">Sem dados ainda.</p>'
    W, H = 1000, 250
    pl, pr, pt, pb = 22, 22, 30, 40
    iw, ih = W - pl - pr, H - pt - pb
    n = len(dados)
    mx = max(v for _, v in dados) or 1
    pts = []
    for i, (ano, v) in enumerate(dados):
        x = pl + (iw * i / (n - 1) if n > 1 else iw / 2)
        y = pt + ih * (1 - v / mx)
        pts.append((x, y, str(ano), v))
    linha = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in pts)
    area = f"{pts[0][0]:.1f},{pt+ih:.0f} {linha} {pts[-1][0]:.1f},{pt+ih:.0f}"
    grid = "".join(
        f'<line x1="{pl}" y1="{pt+ih*f:.0f}" x2="{W-pr}" y2="{pt+ih*f:.0f}" '
        f'stroke="var(--grid)" stroke-width="1"/>' for f in (0.0, 0.5, 1.0))
    passo = 1 if n <= 12 else (n // 10 + 1)
    corpo = []
    for i, (x, y, ano, v) in enumerate(pts):
        corpo.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="transparent">'
                     f'<title>{escape(ano)}: {v}{escape(unidade)}</title></circle>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="var(--series-1)"/>'
                     f'<text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" class="val">{v}{escape(unidade)}</text>')
        if i % passo == 0 or i == n - 1:
            corpo.append(f'<text x="{x:.1f}" y="{H-14}" text-anchor="middle" class="lbl">{escape(ano)}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" style="display:block">'
            f'<defs><linearGradient id="lng" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="var(--series-1)" stop-opacity="0.28"/>'
            f'<stop offset="1" stop-color="var(--series-1)" stop-opacity="0"/></linearGradient></defs>'
            f'{grid}<polygon points="{area}" fill="url(#lng)"/>'
            f'<polyline points="{linha}" fill="none" stroke="var(--series-1)" stroke-width="2.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            + "".join(corpo) + "</svg>")


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


def _squarify(itens: list[tuple], x: float, y: float, w: float, h: float) -> list[tuple]:
    """Layout squarified de treemap (Bruls, Huizing & van Wijk, 2000).

    Recebe `itens = [(chave, valor), ...]` e o retângulo (x, y, w, h) e devolve
    `[(chave, valor, x, y, w, h), ...]` — cada item recebe um retângulo cuja ÁREA
    é proporcional ao valor, buscando quadrados (razão de aspecto ~1) para leitura.
    Itens de valor <= 0 devem ser filtrados ANTES (área nula quebra o layout)."""
    total = sum(v for _, v in itens)
    if total <= 0 or w <= 0 or h <= 0:
        return []
    scale = (w * h) / total
    areas = [(k, v, v * scale) for k, v in itens]  # (chave, valor, área)
    out: list[tuple] = []
    rx, ry, rw, rh = x, y, w, h
    n, i = len(areas), 0

    def _worst(row_areas: list[float], side: float, s: float) -> float:
        mx, mn = max(row_areas), min(row_areas)
        return max((side * side * mx) / (s * s), (s * s) / (side * side * mn))

    while i < n:
        side = min(rw, rh)
        row: list[tuple] = []
        row_area, best, j = 0.0, float("inf"), i
        while j < n:
            cand = [a for _, _, a in row] + [areas[j][2]]
            wst = _worst(cand, side, row_area + areas[j][2])
            if wst <= best:
                row.append(areas[j]); row_area += areas[j][2]; best = wst; j += 1
            else:
                break
        if rw >= rh:  # empilha a fileira como uma COLUNA à esquerda
            col_w = row_area / rh
            yy = ry
            for k, v, a in row:
                hh = a / col_w
                out.append((k, v, rx, yy, col_w, hh)); yy += hh
            rx += col_w; rw -= col_w
        else:         # empilha a fileira como uma LINHA no topo
            row_h = row_area / rw
            xx = rx
            for k, v, a in row:
                ww = a / row_h
                out.append((k, v, xx, ry, ww, row_h)); xx += ww
            ry += row_h; rh -= row_h
        i = j
    return out


def _treemap(grupos: list[dict], *, unidade: str = "") -> str:
    """Treemap (mapa de árvore) de 2 níveis, em SVG puro (sem JS, sem libs).

    Mostra HIERARQUIA + MAGNITUDE num só quadro: cada GRUPO vira um bloco cuja
    área é proporcional ao seu total, subdividido em QUADROS-FILHOS coloridos.
    Bom para "part-of-whole" aninhado (ex.: nicho × status, tema × tipo); ruim
    para série temporal ou comparação numérica precisa.

    COMO USAR
    ---------
    grupos: lista de dicts, um por bloco de 1º nível::

        grupos = [
            {"nome": "Robótica e cultura maker", "tiles": [
                ("ativa",         2028, "var(--ok)"),    # (rótulo, valor, cor)
                ("dormente",       671, "var(--cta)"),
                ("intermediária",  124, "var(--mid)"),
            ]},
            {"nome": "Mulheres e inclusão", "tiles": [ ... ]},
        ]
        html = _treemap(grupos, unidade="")   # -> string SVG, largura 100%

    - O total de cada grupo é a soma dos valores dos seus `tiles` (não passe total).
    - `cor` é qualquer cor CSS; use os tokens do tema (`var(--ok)`, `var(--cta)`,
      `var(--muted)`, `var(--c1..c6)`) para funcionar em claro E escuro.
    - Ordene os `tiles` como quiser; a função reordena por valor (maior primeiro).
    - Rótulo + valor + % (do grupo) aparecem no quadro quando cabem; sempre há um
      `<title>` (tooltip nativo) com o texto completo.
    - LIMITE: valor 0 tem área nula e é descartado (não vira quadro). Informe esses
      casos fora do gráfico (contagem/nota), como fazem as páginas Investimento/Temas.

    Onde é usado: página Investimento (nicho × status) e Temas (tema × tipo) —
    ver `dados_treemap_nicho()` em investimento.py e `dados_treemap_tema()` em temas.py.
    """
    def _fmt(v: int) -> str:
        return f"{v:,}".replace(",", ".")

    grupos = [g for g in grupos if sum(v for _, v, _ in g["tiles"]) > 0]
    if not grupos:
        return '<p class="vazio">Sem dados ainda.</p>'
    W, H, HD, PAD = 1000, 560, 22, 3
    total = sum(sum(v for _, v, _ in g["tiles"]) for g in grupos)
    parents = _squarify(
        [(gi, sum(v for _, v, _ in g["tiles"])) for gi, g in enumerate(grupos)], 0, 0, W, H)
    partes: list[str] = []
    for gi, pv, px, py, pw, ph in parents:
        g = grupos[gi]
        show_hd = ph > HD + 14 and pw > 90
        if show_hd:
            partes.append(
                f'<text x="{px+6:.0f}" y="{py+15:.0f}" class="tm-hd">{escape(g["nome"][:34])}</text>'
                f'<text x="{px+pw-6:.0f}" y="{py+15:.0f}" text-anchor="end" class="tm-hp">'
                f'{_fmt(pv)} · {pv/total*100:.0f}%</text>')
        ix = px + PAD
        iy = py + (HD if show_hd else PAD)
        iw = pw - PAD * 2
        ih = ph - (HD if show_hd else PAD) - PAD
        tiles = sorted((t for t in g["tiles"] if t[1] > 0), key=lambda t: -t[1])
        kids = _squarify([(ti, t[1]) for ti, t in enumerate(tiles)], 0, 0, max(iw, 1), max(ih, 1))
        for ti, kv, kx, ky, kw, kh in kids:
            rot, val, cor = tiles[ti]
            X, Y = ix + kx, iy + ky
            share = kv / pv * 100 if pv else 0
            partes.append(
                f'<g class="tm-tile"><rect x="{X:.1f}" y="{Y:.1f}" width="{kw:.1f}" height="{kh:.1f}" '
                f'rx="4" fill="{cor}" stroke="var(--surface-1)" stroke-width="2"/>'
                f'<title>{escape(g["nome"])} — {escape(rot)}: {_fmt(kv)}{escape(unidade)} '
                f'({share:.0f}% do grupo)</title>')
            if kw > 66 and kh > 40:
                partes.append(
                    f'<text x="{X+7:.1f}" y="{Y+kh-16:.1f}" class="tm-name">{escape(rot[:24])}</text>'
                    f'<text x="{X+7:.1f}" y="{Y+kh-5:.1f}" class="tm-val">{_fmt(kv)}{escape(unidade)} · {share:.0f}%</text>')
            elif kw > 44 and kh > 24:
                partes.append(
                    f'<text x="{X+6:.1f}" y="{Y+kh-6:.1f}" class="tm-val">{_fmt(kv)} · {share:.0f}%</text>')
            partes.append('</g>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
            f'style="display:block;border-radius:8px">{"".join(partes)}</svg>')


# JS do treemap navegável (squarified + drill + tooltip), isolado por container.
_TREEMAP_JS = r"""(function(){
var DATA=__DATA__, ID="__ID__", W=1000,H=560,PAD=2.5,HD=22;
var board=document.getElementById(ID+"-board"),crumbs=document.getElementById(ID+"-crumbs"),
    tip=document.getElementById(ID+"-tip"),drill=null;
var fmt=function(n){return n.toLocaleString('pt-BR');};
function worst(a,side,s){var mx=Math.max.apply(null,a),mn=Math.min.apply(null,a);
  return Math.max(side*side*mx/(s*s),s*s/(side*side*mn));}
function mk(it,x,y,w,h){var o={};for(var k in it)o[k]=it[k];o.x=x;o.y=y;o.w=w;o.h=h;return o;}
function squ(items,x,y,w,h){
  var total=items.reduce(function(s,it){return s+it.value;},0);
  if(total<=0||w<=0||h<=0)return [];
  var scale=w*h/total,nodes=items.map(function(it){return {it:it,area:it.value*scale};}),out=[];
  var rx=x,ry=y,rw=w,rh=h,i=0;
  while(i<nodes.length){
    var side=Math.min(rw,rh),row=[],rowArea=0,best=Infinity,j=i;
    while(j<nodes.length){
      var cand=row.map(function(n){return n.area;}).concat(nodes[j].area);
      var wst=worst(cand,side,rowArea+nodes[j].area);
      if(wst<=best){row.push(nodes[j]);rowArea+=nodes[j].area;best=wst;j++;}else break;
    }
    if(rw>=rh){var cw=rowArea/rh,yy=ry;row.forEach(function(n){var hh=n.area/cw;out.push(mk(n.it,rx,yy,cw,hh));yy+=hh;});rx+=cw;rw-=cw;}
    else{var rh2=rowArea/rw,xx=rx;row.forEach(function(n){var ww=n.area/rh2;out.push(mk(n.it,xx,ry,ww,rh2));xx+=ww;});ry+=rh2;rh-=rh2;}
    i=j;
  }
  return out;
}
function groups(){
  if(!drill){
    return DATA.groups.map(function(g){
      var tiles=g.parts.map(function(p){var c=p[0];return {name:(DATA.labels[c]||c),val:p[1],value:p[1],color:DATA.colors[c]||'#888',cat:c};})
        .filter(function(t){return t.val>0;}).sort(function(a,b){return b.val-a.val;});
      return {name:g.nome,value:tiles.reduce(function(s,t){return s+t.val;},0),clickable:true,tiles:tiles};
    }).filter(function(g){return g.value>0;}).sort(function(a,b){return b.value-a.value;});
  }
  var rows=(DATA.drill[drill]||[]),by={};
  rows.forEach(function(r){(by[r.c]=by[r.c]||[]).push(r);});
  return Object.keys(by).map(function(c){
    return {name:(DATA.labels[c]||c),value:by[c].reduce(function(s,r){return s+r.v;},0),color:DATA.colors[c]||'#888',clickable:false,
      tiles:by[c].map(function(r){return {name:r.t,val:r.v,value:r.v,color:DATA.colors[c]||'#888',cat:c};}).sort(function(a,b){return b.val-a.val;})};
  }).sort(function(a,b){return b.value-a.value;});
}
function ep(g){return 'left:'+(g.x/W*100)+'%;top:'+(g.y/H*100)+'%;width:'+(g.w/W*100)+'%;height:'+(g.h/H*100)+'%';}
function render(){
  var gs=groups(),total=gs.reduce(function(s,g){return s+g.value;},0)||1;
  var laid=squ(gs.map(function(g){return mk(g,0,0,0,0);}),0,0,W,H);
  board.innerHTML='';
  laid.forEach(function(g){
    var showHd=g.h>HD+14&&g.w>76,div=document.createElement('div');
    div.className='tmi-p'+(g.clickable?' clk':'');div.style.cssText=ep(g);
    if(showHd){var hd=document.createElement('div');hd.className='tmi-hd';
      hd.innerHTML='<span style="overflow:hidden;text-overflow:ellipsis">'+g.name+'</span><span class="p">'+fmt(g.value)+' · '+Math.round(g.value/total*100)+'%</span>';
      div.appendChild(hd);}
    if(g.clickable){div.tabIndex=0;div.setAttribute('role','button');div.title='Abrir '+g.name;
      var open=function(){drill=g.name;render();};
      div.addEventListener('click',open);
      div.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();open();}});}
    var ix=PAD,iy=(showHd?HD:PAD),iw=g.w-PAD*2,ih=g.h-(showHd?HD:PAD)-PAD;
    var kids=squ(g.tiles.map(function(t){return mk(t,0,0,0,0);}),0,0,Math.max(iw,1),Math.max(ih,1));
    kids.forEach(function(k){
      var t=document.createElement('div');t.className='tmi-t';
      t.style.cssText='left:'+((ix+k.x)/g.w*100)+'%;top:'+((iy+k.y)/g.h*100)+'%;width:'+(k.w/g.w*100)+'%;height:'+(k.h/g.h*100)+'%;background:'+k.color;
      var sg=k.val/g.value*100,st=k.val/total*100;
      if(k.w>66&&k.h>40)t.innerHTML='<span class="n">'+k.name+'</span><span class="v">'+fmt(k.val)+' <small>· '+Math.round(sg)+'%</small></span>';
      else if(k.w>44&&k.h>24)t.innerHTML='<span class="v">'+fmt(k.val)+'<small> · '+Math.round(sg)+'%</small></span>';
      t.addEventListener('pointerenter',function(e){showTip(e,g,k,sg,st);});
      t.addEventListener('pointermove',moveTip);t.addEventListener('pointerleave',hideTip);
      if(g.clickable)t.style.pointerEvents='none';
      div.appendChild(t);
    });
    board.appendChild(div);
  });
  renderCrumbs();
}
function renderCrumbs(){
  if(!drill){crumbs.innerHTML='<span class="cur">'+DATA.crumb_all+'</span> — clique num quadro para ver as iniciativas';}
  else{var z=DATA.zero[drill]||0,note=z?(' · +'+z+' sem '+DATA.medida+' registrado'):'';
    crumbs.innerHTML='<button type="button">← '+DATA.crumb_all+'</button> › <span class="cur">'+drill+'</span>'+note;
    crumbs.querySelector('button').addEventListener('click',function(){drill=null;render();});}
}
function showTip(e,g,k,sg,st){
  tip.innerHTML='<b>'+k.name+'</b>'+(drill?'<div style="opacity:.8;margin-top:2px">'+DATA.dim+': '+(DATA.labels[k.cat]||k.cat)+' · '+drill+'</div>':'<div style="opacity:.8;margin-top:2px">'+g.name+'</div>')
    +'<div class="r"><span class="k">'+DATA.medida+'</span><span>'+fmt(k.val)+'</span></div>'
    +'<div class="r"><span class="k">'+(drill?'do nicho/tema':'do grupo')+'</span><span>'+Math.round(sg)+'%</span></div>'
    +'<div class="r"><span class="k">do total</span><span>'+st.toFixed(1)+'%</span></div>';
  tip.classList.add('on');moveTip(e);
}
function moveTip(e){var pad=14,tw=tip.offsetWidth,th=tip.offsetHeight,x=e.clientX+pad,y=e.clientY+pad;
  if(x+tw>innerWidth)x=e.clientX-tw-pad;if(y+th>innerHeight)y=e.clientY-th-pad;tip.style.left=x+'px';tip.style.top=y+'px';}
function hideTip(){tip.classList.remove('on');}
addEventListener('resize',render);render();
})();"""


def _treemap_interativo(payload: dict, *, dom_id: str, fallback: str = "") -> str:
    """Treemap NAVEGÁVEL (drill-down) em HTML + JS — categoria › iniciativa.

    Ao contrário de `_treemap` (SVG estático, 1 nível), este permite CLICAR num
    grupo para descer ao 2º nível (as iniciativas daquele grupo, agrupadas pela
    mesma dimensão colorida). Tem breadcrumb de volta, tooltip com %, e degrada
    para o `fallback` (o SVG estático) quando não há JS, via <noscript>.

    COMO USAR
    ---------
    payload: dict serializável em JSON com::

        {
          "dim": "status",              # palavra da dimensão (aparece no tooltip)
          "medida": "público",          # o que o valor conta (tooltip + nota)
          "crumb_all": "Todos os nichos",
          "colors": {"ativa":"var(--ok)", "dormente":"var(--cta)", ...},  # cat -> cor
          "labels": {"ativa":"ativa", "intermediaria":"intermediária"},    # cat -> rótulo (opcional)
          "groups": [                   # NÍVEL 1: um por categoria
             {"nome":"Robótica...", "parts":[["ativa",2028],["dormente",671]]},
          ],
          "drill": {                    # NÍVEL 2: iniciativas por categoria (só valor>0)
             "Robótica...": [{"t":"LAMPEX...", "c":"ativa", "v":1290}, ...],
          },
          "zero": {"Robótica...": 5},   # nº de iniciativas com valor 0 (nota no breadcrumb)
        }

    dom_id: id único do container na página (ex.: "tm-inv", "tm-tem").
    fallback: HTML mostrado dentro de <noscript> (passe `_treemap(...)`).

    Cores devem ser tokens do tema (`var(--ok)`, `var(--c1)`...) p/ claro + escuro.
    Emite: <div#dom_id>(crumbs+board)</div> + <div#dom_id-tip> + <script>.
    Monta os dados com `payload_treemap_nicho()` (investimento.py) e
    `payload_treemap_tema()` (temas.py).
    """
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    js = _TREEMAP_JS.replace("__DATA__", data).replace("__ID__", dom_id)
    nos = f"<noscript>{fallback}</noscript>" if fallback else ""
    return (f'<div class="tmi" id="{dom_id}">'
            f'<div class="tmi-crumbs" id="{dom_id}-crumbs"></div>'
            f'<div class="tmi-board" id="{dom_id}-board" role="img" '
            f'aria-label="Treemap navegável"></div></div>{nos}'
            f'<div class="tmi-tip" id="{dom_id}-tip" role="status" aria-live="polite"></div>'
            f'<script>{js}</script>')


def _lista_acoes(itens: list[tuple]) -> str:
    """Lista rolável de ações (título · tipo · processo · [coordenador])."""
    if not itens:
        return '<p class="vazio">Nenhuma — todas as ações têm participações.</p>'
    linhas = []
    for item in itens:
        t, pr, tp = item[0], item[1], item[2]
        coord = item[3] if len(item) > 3 else None
        chip_coord = (f'<span class="li-coord">{escape(str(coord))}</span>' if coord else "")
        linhas.append(
            f'<div class="li{"4" if coord else ""}"><span class="li-tit">{escape(str(t)[:70])}</span>'
            f'{chip_coord}'
            f'<span class="li-tipo">{escape(str(tp))}</span>'
            f'<span class="li-proc">{escape(str(pr) or "—")}</span></div>'
        )
    return f'<div class="lista">{"".join(linhas)}</div>'


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
    return (f'<svg viewBox="0 0 {lblw+bw+110} {h}" width="100%" role="img" '
            f'style="max-width:{lblw+bw+110}px">'
            + "".join(linhas) + "</svg>")


def _tile(valor, rotulo: str, sub: str = "") -> str:
    subhtml = f'<div class="tile-sub">{escape(sub)}</div>' if sub else ""
    return (f'<div class="tile"><div class="tile-val">{valor}</div>'
            f'<div class="tile-lbl">{escape(rotulo)}</div>{subhtml}</div>')


def _secao(titulo: str, corpo: str, desc: str = "", explica: str = "") -> str:
    """Seção do relatório. `desc` = resumo de 1 linha; `explica` = explicação
    detalhada (o que mede, como é calculado, como interpretar) num bloco
    expansível "O que significa?"."""
    d = f'<p class="sec-desc">{escape(desc)}</p>' if desc else ""
    e = (f'<details class="explica"><summary>O que significa?</summary>'
         f'<p>{escape(explica)}</p></details>' if explica else "")
    return f'<section><h2>{escape(titulo)}</h2>{d}<div class="card">{corpo}{e}</div></section>'


def _secao_par(titulo: str, a: tuple, b: tuple) -> str:
    """Uma seção com DOIS gráficos lado a lado (economiza espaço).
    Cada item = (subtitulo, corpo_html, desc, explica)."""
    def _item(sub, corpo, desc="", explica=""):
        d = f'<p class="sec-desc" style="margin:0 0 8px">{escape(desc)}</p>' if desc else ""
        ex = (f'<details class="explica"><summary>O que significa?</summary>'
              f'<p>{escape(explica)}</p></details>' if explica else "")
        return (f'<div class="par2-item"><h3 class="par2-h">{escape(sub)}</h3>{d}{corpo}{ex}</div>')
    return (f'<section><h2>{escape(titulo)}</h2>'
            f'<div class="card"><div class="par2">{_item(*a)}{_item(*b)}</div></div></section>')


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
.explica{margin-top:12px;border-top:1px dashed var(--grid);padding-top:8px}
.explica summary{cursor:pointer;color:var(--series-1);font-size:.82rem;font-weight:600}
.explica p{color:var(--text-secondary);font-size:.84rem;margin:8px 0 0;max-width:70ch}
.lista{max-height:340px;overflow-y:auto;display:flex;flex-direction:column;gap:1px}
.li{display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:center;
padding:7px 4px;border-bottom:1px solid var(--grid);font-size:.85rem}
.li4{grid-template-columns:1fr auto auto auto}
.li-coord{color:var(--text-secondary);font-size:.78rem;white-space:nowrap}
.li-tit{color:var(--text-primary)}
.li-tipo{color:var(--muted);font-size:.75rem;border:1px solid var(--border);border-radius:20px;padding:1px 8px}
.li-proc{color:var(--text-secondary);font-variant-numeric:tabular-nums;font-size:.8rem}
"""


def blocos_relatorio(a: dict) -> tuple[str, str]:
    """Devolve (tiles_html, secoes_html) do relatório-base para um agregado `a`."""
    com_filtro = a["n_processos_part"] > 0
    tiles = "".join([
        _tile(a["n_acoes_ativas"] if com_filtro else a["n_acoes"], "Ações com participação",
              f'de {a["n_acoes"]} cadastradas' if com_filtro else ""),
        _tile(a["total_atividades"] or "—", "Atividades com participação",
              f'{a["n_processos_part"]} processos'),
        _tile(a["total_publico"] or "—", "Alunos atendidos"),
        _tile(a["total_equipe"] or "—", "Equipe executora", f'média {a["media_equipe"]:.1f}/ação'),
        _tile(f'{a["taxa_cert"]:.0f}%' if a["total_publico"] else "—", "Taxa de certificação"),
    ])

    # seções de ações (sempre)
    secoes = [
        _secao_par(
            "Ações por natureza e tipo",
            ("Ações por natureza", _barras(a["natureza"]),
             "Distribuição das ações por natureza acadêmica.",
             "Conta quantas ações registradas no SRC pertencem a cada natureza "
             "(Extensão, Ensino, Pesquisa, Pós-Graduação ou Desenvolvimento Institucional). "
             "Cada ação conta uma vez, pela natureza declarada no cadastro. "
             "Serve para ver o perfil do campus: predominância de Extensão indica "
             "vocação de atendimento à comunidade externa."),
            ("Ações por tipo", _donut(a["tipo"]),
             "Programa, Projeto, Curso, Evento e demais tipos.",
             "Formato de execução declarado no cadastro de cada ação. "
             "Programa = iniciativa contínua que costuma abrigar outras ações; "
             "Projeto = ação com início/fim e objetivos próprios; Curso = formação com carga "
             "horária e turma; Evento = atividade pontual (palestra, semana, feira). "
             "A leitura conjunta com a natureza mostra COMO o campus atua, não só quanto.")),
        _secao_par(
            "Fomento e relatório final",
            ("Fomento (top 8)", _barras(a["fomento"]),
             "Fonte de fomento vinculada à ação.",
             "Origem do apoio financeiro declarada no cadastro (FAPES, PAEX-IFES, "
             "PRONATEC etc.). 'SEM VÍNCULO' significa que a ação não declarou fonte de fomento — "
             "geralmente executada só com recursos próprios/voluntariado. Percentual alto de "
             "SEM VÍNCULO sinaliza baixa captação de recursos externos."),
            ("Relatório aprovado", _donut(a["relatorio"]),
             "Ações com relatório final aprovado.",
             "Situação do relatório final da ação no SRC: 'Sim' significa relatório "
             "entregue e aprovado; 'Não' inclui ações em andamento, encerradas sem relatório ou "
             "com relatório pendente. É um termômetro de conclusão formal do ciclo da ação.")),
        _secao("Ações por ano de cadastro", _linha(a["anos"]),
               "Volume de ações cadastradas por ano.",
               explica="Quantidade de ações registradas no SRC em cada ano (pela data de cadastro, "
               "não pela data de execução). Mostra a tendência histórica de produção do campus. "
               "Atenção: o ano corrente sempre parece menor porque ainda está em curso, e quedas "
               "em 2020–2021 refletem a pandemia."),
        _secao_par(
            "Grande área e área temática",
            ("Grande área do conhecimento", _donut(a["grande_area"]),
             f'{a["n_ga_inferida"]} categorias inferidas por IA (Mistral) a partir do resumo.',
             "Classificação CNPq da ação (Engenharias, Ciências Humanas etc.). "
             "Como mais da metade dos cadastros originais deixou o campo vazio, as categorias "
             "faltantes foram deduzidas por IA (Mistral) lendo título + resumo da ação, sempre "
             "escolhendo dentro da tabela oficial e só quando a confiança é ≥ 60%. O valor "
             "original nunca é sobrescrito: a inferência fica marcada no dado como '(inferida)'."),
            ("Área temática principal", _donut(a["area_tematica"]),
             f'{a["n_at_inferida"]} categorias inferidas por IA (Mistral) a partir do resumo.',
             "Área temática da extensão (Educação, Saúde, Cultura, Tecnologia e Produção...), "
             "conforme o dropdown oficial do SRC. Mesma regra da grande área: vazios foram "
             "completados por IA com base no resumo, marcados como inferidos e limitados às "
             "categorias que já existem no sistema.")),
    ]
    # seções de participação (só quando há dados coletados)
    if a["n_processos_part"]:
        secoes += [
            _secao_par(
                "Top 10 — coordenadores e ações",
                ("Coordenadores por nº de ações", _barras(a["coordenadores"]),
                 "Proponentes mais recorrentes — só ações com participação registrada.",
                 "Ranking dos coordenadores(as) pelo número de ações em que constam como "
                 "responsáveis. Ações sem nenhum participante registrado (público e equipe zerados) "
                 "são EXCLUÍDAS desta contagem, para medir produção efetiva e não apenas cadastros. "
                 "Coordenador é dado público do sistema."),
                ("Ações por alunos atendidos", _barras(a["top_publico"]),
                 "Ações com maior público-alvo (participações).",
                 "Soma, por ação, de todas as pessoas registradas como público-alvo nas "
                 "suas atividades. Mede alcance bruto (inscrições/atendimentos), não pessoas "
                 "únicas — a mesma pessoa em duas atividades conta duas vezes aqui. Títulos "
                 "repetidos (ex.: 'Ifes Portas Abertas') são edições distintas, com processos "
                 "diferentes.")),
            _secao_par(
                "Situação e certificação do público-alvo",
                ("Situação dos participantes", _donut(a["situacao"]),
                 "Situação registrada do público-alvo.",
                 "Status final de cada participação de público-alvo conforme lançado no "
                 "SRC: APROVADO (concluiu com êxito), CURSANDO (em andamento), REPROVADO (não "
                 "atingiu os critérios). A base é participações, não pessoas — uma pessoa pode "
                 "estar APROVADO numa atividade e CURSANDO em outra."),
                ("Certificação do público-alvo", _donut(a["certificado"]),
                 "Participações com certificado emitido.",
                 "Percentual das participações de público-alvo com certificado emitido "
                 "no SRC. 'Não emitido' inclui em andamento (ainda sem direito), reprovados e "
                 "casos onde o coordenador não emitiu. É indicador de entrega formal do "
                 "benefício ao participante.")),
            _secao("Equipe executora por função (top 8)", _barras(a["funcao"]),
                   explica="Composição de quem EXECUTA as ações, pela função declarada de cada "
                   "vínculo de equipe: bolsistas, voluntários, coordenador, professores etc. "
                   "Mede a força de trabalho da extensão — em particular o protagonismo discente "
                   "(funções de aluno) frente ao corpo docente."),
        ]
        if a["nao_coletados"]:
            secoes.append(_secao(
                f"Ações não coletadas ({len(a['nao_coletados'])})",
                _lista_acoes(a["nao_coletados"]),
                "Processo cujo detalhamento de participações falhou na extração."))
    return tiles, "".join(secoes)


def gerar_relatorio(
    acoes_dir: str | Path = "data/serra",
    part_dir: str | Path = "data/participacoes",
    out_html: str | Path = "relatorio.html",
    *,
    titulo: str = "SRC/Ifes — Campus Serra",
) -> Path:
    a = agregar(_carregar_acoes(acoes_dir), _carregar_participacoes(part_dir))
    tiles, secoes_html = blocos_relatorio(a)

    html = f"""<div class="wrap">
<header>
  <h1>{escape(titulo)}</h1>
  <p class="sub">Relatório analítico — dados extraídos do SRC/Ifes</p>
</header>
<div class="tiles">{tiles}</div>
{secoes_html}
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
