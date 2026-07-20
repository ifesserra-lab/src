"""Cruzamento formados × participação em Extensão.

Lê as planilhas de formados (data/formandos/*.xlsx) e cruza, por NOME
normalizado (as planilhas não têm CPF), com o público-alvo e a equipe das ações
de natureza Extensão no consolidado. Produz contagens agregadas (sem nomes).

Ressalva: casamento por nome pode ter homônimos/variações — com CPF seria exato.
"""

from __future__ import annotations

import glob
import unicodedata
from collections import Counter
from pathlib import Path

from .relatorio import _barras, _donut, _secao, _secao_par, _tile


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def _carregar_formados(formandos_dir: str | Path) -> dict[str, tuple[str, str]]:
    """{matricula: (nome, curso)} deduplicado entre as planilhas."""
    import openpyxl
    formados: dict[str, tuple[str, str]] = {}
    for f in glob.glob(str(Path(formandos_dir) / "*.xlsx")):
        ws = openpyxl.load_workbook(f, read_only=True).active
        it = ws.iter_rows(values_only=True)
        next(it, None)  # cabeçalho
        for r in it:
            if r and r[0]:
                curso = r[3] if len(r) > 3 else ""
                formados[str(r[0]).strip()] = (r[1], curso)
    return formados


def agregar_formados(consolidado: dict, formandos_dir: str | Path = "data/formandos") -> dict:
    formados = _carregar_formados(formandos_dir)
    nome2mat = {_norm(nome): mat for mat, (nome, _c) in formados.items()}
    curso_por_mat = {mat: (curso or "—") for mat, (_n, curso) in formados.items()}

    ext_pub, ext_eq = set(), set()   # nomes normalizados em Extensão
    for a in consolidado.get("acoes", []):
        if "extens" not in _norm(a.get("Natureza")):
            continue
        for p in a.get("participacoes", []):
            n = _norm(p.get("Nome"))
            if p.get("tipo", "").startswith("Público"):
                ext_pub.add(n)
            else:
                ext_eq.add(n)

    setf = set(nome2mat)
    mat_pub = {nome2mat[n] for n in setf & ext_pub}
    mat_eq = {nome2mat[n] for n in setf & ext_eq}
    mat_any = mat_pub | mat_eq
    total = len(formados)

    # por curso: formados totais vs participantes (público OU equipe)
    curso_total = Counter(curso_por_mat.values())
    curso_part = Counter(curso_por_mat[m] for m in mat_any)
    por_curso = sorted(
        [(c, curso_part.get(c, 0), n) for c, n in curso_total.items()],
        key=lambda x: -x[1])[:6]

    return {
        "total_formados": total,
        "em_ext_publico": len(mat_pub),
        "em_ext_equipe": len(mat_eq),
        "em_ext_qualquer": len(mat_any),
        "pct_qualquer": (len(mat_any) / total * 100) if total else 0,
        "participou_dist": [("Participou da Extensão", len(mat_any)),
                            ("Sem registro", total - len(mat_any))],
        "papel_dist": [("Só público-alvo", len(mat_pub - mat_eq)),
                       ("Só equipe", len(mat_eq - mat_pub)),
                       ("Ambos", len(mat_pub & mat_eq))],
        "por_curso": [(f"{c[:26]} ({part}/{tot})", part) for c, part, tot in por_curso],
    }


def blocos_formados(a: dict) -> tuple[str, str]:
    tiles = "".join([
        _tile(a["total_formados"], "Formados (distintos)", "2020–2025"),
        _tile(a["em_ext_qualquer"], "Participaram da Extensão", f'{a["pct_qualquer"]:.0f}% do total'),
        _tile(a["em_ext_publico"], "Como público-alvo"),
        _tile(a["em_ext_equipe"], "Como equipe executora"),
    ])
    secoes = [
        _secao_par(
            "Formados que participaram de Extensão",
            ("Participação",
             _donut(a["participou_dist"]),
             "Formados com ao menos uma participação (público-alvo ou equipe) em ação de Extensão.",
             "Cruza a lista oficial de formados do campus (planilhas acadêmicas 2020–2025, "
             "deduplicadas por matrícula) com os participantes das ações de natureza Extensão. "
             "'Participou' = o nome do formado aparece ao menos uma vez como público-alvo OU membro "
             "de equipe. Como as planilhas não trazem CPF, o casamento é por nome normalizado — "
             "homônimos ou grafias diferentes podem gerar pequeno erro."),
            ("Papel na Extensão",
             _donut(a["papel_dist"]),
             "Como o formado participou: público-alvo, equipe executora ou ambos.",
             "Entre os formados que participaram: 'Só público-alvo' foi atendido por ações (fez "
             "curso, participou de evento); 'Só equipe' atuou executando (bolsista, voluntário); "
             "'Ambos' viveu os dois lados — tipicamente quem foi atendido e depois virou executor, "
             "o ciclo virtuoso da extensão.")),
        _secao("Formados na Extensão por curso (participantes/total)", _barras(a["por_curso"]),
               "Nº de formados de cada curso que participaram da Extensão.",
               explica="Recorte por curso de graduação: quantos formados de cada curso têm "
               "registro de participação em extensão (o rótulo mostra participantes/total do "
               "curso). Permite comparar o quanto cada curso expõe seus alunos à extensão antes "
               "de formar."),
    ]
    return tiles, "".join(secoes)
