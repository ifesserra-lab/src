"""Jornada do formado: ingresso (matrícula) × 1ª extensão × formatura.

Cruza as planilhas de formados (matrícula codifica ano/semestre de ingresso;
o arquivo mais antigo em que a matrícula aparece indica o semestre de formatura)
com a primeira participação em ação de Extensão (por nome normalizado).

Resultados são agregados (contagens, medianas, distribuições) — nunca expõem
matrícula, CPF ou nome ligado a data pessoal.

Ressalvas: casamento por nome (planilhas não têm CPF) pode ter homônimos;
granularidade semestral; formatura = 1ª aparição nas planilhas.
"""

from __future__ import annotations

import glob
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

_MAT = re.compile(r"^(\d{4})(\d)([A-Z]+)")
_ARQ = re.compile(r"formados_(\d{4})_(\d)")


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def _data(s) -> datetime | None:
    try:
        return datetime.strptime((s or "").strip(), "%d/%m/%Y")
    except (ValueError, AttributeError):
        return None


def _sem(ano: int, sem: int) -> float:
    """Semestre como número decimal (2020.0 = 1º sem; 2020.5 = 2º sem)."""
    return ano + (0.0 if sem == 1 else 0.5)


def _carregar_formados(formandos_dir: str | Path) -> dict[str, dict]:
    import openpyxl
    form: dict[str, dict] = {}
    for f in sorted(glob.glob(str(Path(formandos_dir) / "formados_*.xlsx"))):
        m = _ARQ.search(f)
        if not m:
            continue
        formatura = (int(m.group(1)), int(m.group(2)))
        ws = openpyxl.load_workbook(f, read_only=True).active
        it = ws.iter_rows(values_only=True)
        next(it, None)
        for r in it:
            if not r or not r[0]:
                continue
            mat = str(r[0]).strip()
            x = _MAT.match(mat)
            if not x:
                continue
            reg = form.get(mat)
            if reg is None:
                form[mat] = {"nome": r[1], "curso": (r[3] if len(r) > 3 else "") or "—",
                             "ing": (int(x.group(1)), int(x.group(2))),
                             "form": formatura, "prefixo": x.group(3)}
            elif formatura < reg["form"]:
                reg["form"] = formatura
    return form


def agregar_jornada(consolidado: dict, formandos_dir: str | Path = "data/formandos") -> dict:
    form = _carregar_formados(formandos_dir)

    prim_ext: dict[str, tuple[datetime, str]] = {}
    for a in consolidado.get("acoes", []):
        if "extens" not in _norm(a.get("Natureza")):
            continue
        titulo = (str(a.get("Título ação") or "").strip()) or "—"
        for p in a.get("participacoes", []):
            n = _norm(p.get("Nome"))
            i = _data(p.get("Início"))
            if n and i and (n not in prim_ext or i < prim_ext[n][0]):
                prim_ext[n] = (i, titulo)

    com_ext = 0
    ing_ext, ext_form, dur = [], [], []
    fase = Counter()
    decis = [0] * 10             # posição da 1ª extensão na trajetória (0–100%)
    ing_ano = Counter()          # participações em extensão por ano de ingresso
    curso_tot, curso_ext = Counter(), Counter()
    inic_ano: dict[int, Counter] = defaultdict(Counter)   # iniciativa da 1ª extensão por ano após ingresso
    apos_formar = 0

    for fo in form.values():
        ingd = _sem(*fo["ing"])
        formd = _sem(*fo["form"])
        dur.append(formd - ingd)
        curso_tot[fo["curso"]] += 1
        n = _norm(fo["nome"])
        e = prim_ext.get(n)
        if not e:
            continue
        edata, etitulo = e
        com_ext += 1
        curso_ext[fo["curso"]] += 1
        extd = edata.year + (0.0 if edata.month <= 6 else 0.5)
        ing_ext.append(extd - ingd)
        ext_form.append(formd - extd)
        ing_ano[fo["ing"][0]] += 1
        if extd - ingd >= -0.5:
            inic_ano[max(0, round(extd - ingd))][etitulo] += 1
        if extd > formd + 0.05:
            apos_formar += 1
        if formd > ingd:
            frac = (extd - ingd) / (formd - ingd)
            fase["No início (0–33%)" if frac < 0.33 else "No meio (33–66%)" if frac < 0.66
                 else "No fim (66–100%)" if frac <= 1.05 else "Após formar"] += 1
            if 0 <= frac <= 1:
                decis[min(9, int(frac * 10))] += 1

    def _dist_anos(vals):
        c = Counter(max(0, round(v)) for v in vals if v >= -0.5)
        return [(f"{k} ano(s)", c[k]) for k in sorted(c)]

    por_curso = sorted(
        [(c, curso_ext.get(c, 0), n) for c, n in curso_tot.items()], key=lambda x: -x[2])

    inic_por_ano = []
    for k in sorted(inic_ano):
        c = inic_ano[k]
        tot = sum(c.values())
        itens = [(t, q, round(q / tot * 100)) for t, q in c.most_common()]
        inic_por_ano.append({"ano": f"{k} ano(s)", "k": k, "total": tot, "itens": itens})

    ordem_fase = ["No início (0–33%)", "No meio (33–66%)", "No fim (66–100%)", "Após formar"]
    return {
        "n_formados": len(form),
        "com_ext": com_ext,
        "pct_ext": (com_ext / len(form) * 100) if form else 0,
        "med_ing_ext": statistics.median(ing_ext) if ing_ext else 0,
        "med_ext_form": statistics.median(ext_form) if ext_form else 0,
        "med_dur": statistics.median(dur) if dur else 0,
        "apos_formar": apos_formar,
        "dist_ing_ext": _dist_anos(ing_ext),
        "inic_por_ano": inic_por_ano,
        "fase": [(k, fase[k]) for k in ordem_fase if fase[k]],
        "decis": decis,
        "por_curso": [(f"{c[:26]} ({e}/{n})", round(e / n * 100)) for c, e, n in por_curso if n],
    }


def svg_timeline(a: dict) -> str:
    """Linha do tempo média da jornada: Ingresso → 1ª extensão → Formatura."""
    dur = a["med_dur"] or 4
    p_ext = max(0.08, min(0.9, (a["med_ing_ext"] or 0) / dur))  # posição relativa
    W, H, y = 900, 150, 78
    x0, x1 = 70, W - 70
    x_ext = x0 + (x1 - x0) * p_ext
    sub_ext = f'+{a["med_ing_ext"]:.1f} anos'.replace(".", ",")
    sub_form = f'curso ~{a["med_dur"]:.0f} anos'.replace(".", ",")

    def marco(x, titulo, sub, cor="var(--series-1)"):
        return (f'<circle cx="{x:.0f}" cy="{y}" r="9" fill="{cor}" stroke="var(--surface-1)" stroke-width="3"/>'
                f'<text x="{x:.0f}" y="{y-22}" text-anchor="middle" class="tl-t">{escape(titulo)}</text>'
                f'<text x="{x:.0f}" y="{y+30}" text-anchor="middle" class="tl-s">{escape(sub)}</text>')

    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" style="max-width:{W}px">'
        f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="var(--grid)" stroke-width="4" stroke-linecap="round"/>'
        f'<line x1="{x0}" y1="{y}" x2="{x_ext:.0f}" y2="{y}" stroke="var(--series-1)" stroke-width="4" stroke-linecap="round" opacity=".55"/>'
        + marco(x0, "Ingresso", "matrícula")
        + marco(x_ext, "1ª extensão", sub_ext)
        + marco(x1, "Formatura", sub_form, "var(--text-secondary)")
        + '</svg>')


def svg_curva_fase(a: dict) -> str:
    """Área: densidade de quando (0–100% do curso) acontece a 1ª extensão."""
    dec = a["decis"]
    if not any(dec):
        return '<p class="vazio">Sem dados.</p>'
    W, H, pad = 900, 220, 34
    iw, ih = W - 2 * pad, H - 2 * pad
    mx = max(dec) or 1
    n = len(dec)
    pts = []
    for i, v in enumerate(dec):
        x = pad + iw * (i + 0.5) / n
        yv = pad + ih * (1 - v / mx)
        pts.append((x, yv))
    linha = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    area = (f'{pad},{pad+ih} ' + linha + f' {pad+iw},{pad+ih}')
    barras = "".join(
        f'<text x="{pts[i][0]:.0f}" y="{pts[i][1]-8:.0f}" text-anchor="middle" class="val">{v}</text>'
        for i, v in enumerate(dec) if v)
    eixo = (f'<text x="{pad}" y="{H-8}" class="tl-s">Ingresso</text>'
            f'<text x="{pad+iw}" y="{H-8}" text-anchor="end" class="tl-s">Formatura</text>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" style="max-width:{W}px">'
            f'<polyline points="{area}" fill="var(--series-1)" fill-opacity=".14" stroke="none"/>'
            f'<polyline points="{linha}" fill="none" stroke="var(--series-1)" stroke-width="2.5" '
            f'stroke-linejoin="round"/>'
            + "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3.5" fill="var(--series-1)"/>'
                      for x, y in pts)
            + barras + eixo + '</svg>')


_CAT = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]


def _cores_inic(a: dict, top: int = 7) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Mapeia as `top` iniciativas mais frequentes (no total) para cores fixas.
    Retorna (titulo->cor, legenda ordenada). O resto cai em 'Outras' (muted)."""
    tot = Counter()
    for linha in a.get("inic_por_ano", []):
        for t, q, _ in linha["itens"]:
            tot[t] += q
    principais = [t for t, _ in tot.most_common(top)]
    cor = {t: _CAT[i % len(_CAT)] for i, t in enumerate(principais)}
    leg = [(t, cor[t]) for t in principais]
    if len(tot) > len(principais):
        leg.append(("Outras iniciativas", "var(--muted)"))
    return cor, leg


def svg_inic_stack(a: dict) -> str:
    """Barra 100% empilhada por ano após ingresso: composição das iniciativas
    (ação da 1ª extensão). Mostra a virada de 'Física/Tutorias' para 'LAMPEX'."""
    linhas = a.get("inic_por_ano", [])
    if not linhas:
        return '<p class="vazio">Sem dados.</p>'
    cor, leg = _cores_inic(a)
    ordem = {t: i for i, (t, _) in enumerate(leg)}
    W, lh, lblw, pad = 900, 34, 128, 8
    bw = W - lblw - 70
    H = len(linhas) * lh + pad
    corpo = []
    for i, ln in enumerate(linhas):
        y = i * lh + pad
        tot = ln["total"] or 1
        # agrupa itens fora do top em 'Outras' e ordena pela legenda (cores alinhadas)
        segs: dict[str, int] = defaultdict(int)
        for t, q, _ in ln["itens"]:
            segs["Outras iniciativas" if t not in cor else t] += q
        itens = sorted(segs.items(), key=lambda kv: ordem.get(kv[0], 999))
        corpo.append(f'<text x="{lblw-8}" y="{y+22}" text-anchor="end" class="lbl">{escape(ln["ano"])}</text>')
        x = lblw
        for t, q in itens:
            w = q / tot * bw
            c = cor.get(t, "var(--muted)")
            pct = round(q / tot * 100)
            corpo.append(
                f'<rect x="{x:.1f}" y="{y+7}" width="{max(0.6, w):.1f}" height="{lh-14}" '
                f'fill="{c}"><title>{escape(ln["ano"])} — {escape(t)}: {q} ({pct}%)</title></rect>')
            if w > 34:
                corpo.append(f'<text x="{x+w/2:.1f}" y="{y+23}" text-anchor="middle" '
                             f'class="val" fill="#fff">{pct}%</text>')
            x += w
        corpo.append(f'<text x="{x+8:.1f}" y="{y+23}" class="lbl">{ln["total"]}</text>')
    legenda = ('<div class="leg" style="flex-direction:row;gap:16px;margin-top:12px;flex-wrap:wrap">'
               + "".join(f'<span class="leg-item"><span class="sw" style="background:{c}"></span>'
                         f'{escape(t[:34])}</span>' for t, c in leg) + '</div>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" style="display:block">'
            + "".join(corpo) + "</svg>" + legenda)


def tabela_inic_ano(a: dict) -> str:
    """Tabela completa: por ano após ingresso, cada iniciativa da 1ª extensão,
    nº de alunos e % dentro do ano."""
    linhas = a.get("inic_por_ano", [])
    if not linhas:
        return '<p class="vazio">Sem dados.</p>'
    rows = []
    for ln in linhas:
        itens = ln["itens"]
        for j, (t, q, pct) in enumerate(itens):
            ano_cel = (f'<td rowspan="{len(itens)}" class="ja-ano">{escape(ln["ano"])}'
                       f'<span class="ja-tot">{ln["total"]} alunos</span></td>') if j == 0 else ""
            rows.append(f'<tr>{ano_cel}<td>{escape(t)}</td>'
                        f'<td class="ja-num">{q}</td><td class="ja-num">{pct}%</td></tr>')
    return (f'<div class="card" style="margin-top:14px;overflow:auto"><table class="tb">'
            f'<tr><th>Anos após ingresso</th><th>Iniciativa (1ª extensão)</th>'
            f'<th>Alunos</th><th>% do ano</th></tr>{"".join(rows)}</table></div>')


def texto_inic_ano(a: dict) -> str:
    """Parágrafo descritivo (derivado dos dados) do padrão de entrada por ano."""
    linhas = a.get("inic_por_ano", [])
    if not linhas:
        return ""
    por_k = {ln["k"]: ln for ln in linhas}

    def _top(ks):
        c = Counter()
        for k in ks:
            for t, q, _ in por_k.get(k, {}).get("itens", []):
                c[t] += q
        tot = sum(c.values())
        if not tot:
            return None
        t, q = c.most_common(1)[0]
        return t, round(q / tot * 100)

    cedo, meio = _top([0, 1]), _top([2, 3, 4])
    p = []
    if cedo:
        p.append(f"<b>Entrada precoce (0–1 ano):</b> a porta de entrada é <b>{escape(cedo[0])}</b> "
                 f"(~{cedo[1]}% das 1ªs extensões nesse período) — ações de ensino/monitoria, "
                 f"de baixo custo de adesão para o calouro.")
    if meio:
        p.append(f"<b>A partir do 2º ano:</b> predomina <b>{escape(meio[0])}</b> "
                 f"(~{meio[1]}% entre 2 e 4 anos) — laboratório de práticas, com o aluno já "
                 f"maduro no curso.")
    p.append("A <b>cauda longa</b> reúne dezenas de ações com 1 aluno cada (projetos de P&D "
             "específicos), somando fatia relevante em todos os anos.")
    return "".join(f"<p>{x}</p>" for x in p)


def svg_funil(a: dict) -> str:
    """Funil: formados -> fizeram extensão -> voltaram após formar."""
    etapas = [("Formados", a["n_formados"], "var(--muted)"),
              ("Fizeram extensão", a["com_ext"], "var(--series-1)"),
              ("Ativos após formar", a["apos_formar"], "var(--cta)")]
    base = a["n_formados"] or 1
    W, lh = 900, 54
    linhas = []
    for i, (rot, val, cor) in enumerate(etapas):
        w = max(40, (val / base) * (W - 220))
        yv = i * lh + 6
        pct = round(val / base * 100)
        linhas.append(
            f'<text x="200" y="{yv+30}" text-anchor="end" class="lbl">{escape(rot)}</text>'
            f'<rect x="210" y="{yv+8}" width="{w:.0f}" height="34" rx="6" fill="{cor}"/>'
            f'<text x="{210+w+10:.0f}" y="{yv+30}" class="val">{val} · {pct}%</text>')
    return (f'<svg viewBox="0 0 {W} {len(etapas)*lh+12}" width="100%" role="img" '
            f'style="max-width:{W}px">'
            + "".join(linhas) + "</svg>")
