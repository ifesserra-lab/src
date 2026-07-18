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

    prim_ext: dict[str, datetime] = {}
    for a in consolidado.get("acoes", []):
        if "extens" not in _norm(a.get("Natureza")):
            continue
        for p in a.get("participacoes", []):
            n = _norm(p.get("Nome"))
            i = _data(p.get("Início"))
            if n and i and (n not in prim_ext or i < prim_ext[n]):
                prim_ext[n] = i

    com_ext = 0
    ing_ext, ext_form, dur = [], [], []
    fase = Counter()
    ing_ano = Counter()          # participações em extensão por ano de ingresso
    curso_tot, curso_ext = Counter(), Counter()
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
        com_ext += 1
        curso_ext[fo["curso"]] += 1
        extd = e.year + (0.0 if e.month <= 6 else 0.5)
        ing_ext.append(extd - ingd)
        ext_form.append(formd - extd)
        ing_ano[fo["ing"][0]] += 1
        if extd > formd + 0.05:
            apos_formar += 1
        if formd > ingd:
            frac = (extd - ingd) / (formd - ingd)
            fase["No início (0–33%)" if frac < 0.33 else "No meio (33–66%)" if frac < 0.66
                 else "No fim (66–100%)" if frac <= 1.05 else "Após formar"] += 1

    def _dist_anos(vals):
        c = Counter(max(0, round(v)) for v in vals if v >= -0.5)
        return [(f"{k} ano(s)", c[k]) for k in sorted(c)]

    por_curso = sorted(
        [(c, curso_ext.get(c, 0), n) for c, n in curso_tot.items()], key=lambda x: -x[2])

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
        "fase": [(k, fase[k]) for k in ordem_fase if fase[k]],
        "por_curso": [(f"{c[:26]} ({e}/{n})", round(e / n * 100)) for c, e, n in por_curso if n],
    }
