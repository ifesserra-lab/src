"""Indicadores avançados a partir do JSON consolidado (ação + participações).

Produz um HTML self-contained com métricas que o relatório-base não tem:
alcance real (alunos únicos), recorrência, público por ano, impacto por
coordenador, aprovação/certificação por tipo, composição da equipe, tamanho de
turma. Reaproveita a paleta e os gráficos de `relatorio`.

Sem PII: o CPF é usado apenas para deduplicar/contar; nunca é exibido.

CLI:  src-etl-indicadores --consolidado data/serra_consolidado.json --out indicadores.html
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from .relatorio import _CSS, _barras, _donut, _secao, _tile


def _ano(dc: str | None) -> str:
    return dc.split("/")[-1] if dc and "/" in dc else "?"


def _cert_emitido(v: str | None) -> bool:
    s = (v or "").strip().lower()
    return bool(s) and s not in ("não", "nao", "-")


def _classe_funcao(f: str | None) -> str:
    s = (f or "").upper()
    if "ALUNO" in s or "DISCENTE" in s or "BOLSISTA" in s:
        return "Discente"
    if "PROFESSOR" in s or "DOCENTE" in s:
        return "Docente"
    if "TÉCNICO" in s or "TECNICO" in s or "TAE" in s:
        return "Técnico(a)"
    return "Outros"


def _faixa_turma(n: int) -> str:
    if n <= 10:
        return "1–10"
    if n <= 25:
        return "11–25"
    if n <= 50:
        return "26–50"
    if n <= 100:
        return "51–100"
    return "100+"


def agregar_indicadores(consolidado: dict) -> dict:
    acoes = consolidado.get("acoes", [])

    cpf_publico = set()
    cpf_equipe = set()
    recorrencia = Counter()               # CPF -> nº de participações (público)
    publico_por_ano = Counter()
    publico_por_coord = Counter()
    aprovado_por_tipo = defaultdict(lambda: [0, 0])   # tipo -> [aprovados, total]
    cert_por_tipo = defaultdict(lambda: [0, 0])       # tipo -> [emitidos, total]
    composicao_equipe = Counter()
    turma_por_atividade = Counter()       # (proc, ativ) -> nº público
    total_publico = total_equipe = 0

    for a in acoes:
        tipo = a.get("Tipo ação") or "—"
        ano = _ano(a.get("Data de cadastro"))
        coord = (a.get("Coordenador(a)") or "—").strip() or "—"
        for p in a.get("participacoes", []):
            if p.get("tipo", "").startswith("Público"):
                total_publico += 1
                cpf = (p.get("CPF") or "").strip()
                if cpf:
                    cpf_publico.add(cpf)
                    recorrencia[cpf] += 1
                publico_por_ano[ano] += 1
                publico_por_coord[coord] += 1
                aprovado_por_tipo[tipo][1] += 1
                if (p.get("Situação") or "").strip().upper() == "APROVADO":
                    aprovado_por_tipo[tipo][0] += 1
                cert_por_tipo[tipo][1] += 1
                if _cert_emitido(p.get("Certificado")):
                    cert_por_tipo[tipo][0] += 1
                turma_por_atividade[(a.get("Processo nº"), p.get("atividade_num"))] += 1
            else:  # equipe
                total_equipe += 1
                cpf = (p.get("CPF") or "").strip()
                if cpf:
                    cpf_equipe.add(cpf)
                composicao_equipe[_classe_funcao(p.get("Função"))] += 1

    # recorrência -> faixas
    faixas_rec = Counter()
    for _, n in recorrencia.items():
        faixas_rec["1 ação" if n == 1 else "2 ações" if n == 2
                    else "3–4 ações" if n <= 4 else "5+ ações"] += 1
    ordem_rec = ["1 ação", "2 ações", "3–4 ações", "5+ ações"]
    recorrencia_dist = [(k, faixas_rec[k]) for k in ordem_rec if faixas_rec[k]]

    # turma -> faixas
    faixas_turma = Counter(_faixa_turma(n) for n in turma_por_atividade.values())
    ordem_turma = ["1–10", "11–25", "26–50", "51–100", "100+"]
    turma_dist = [(k, faixas_turma[k]) for k in ordem_turma if faixas_turma[k]]

    def _pct_tipo(d: dict) -> list[tuple[str, int]]:
        out = [(t, round(v[0] / v[1] * 100) if v[1] else 0) for t, v in d.items()]
        return sorted(out, key=lambda x: -x[1])

    alunos_unicos = len(cpf_publico)
    turma_media = (total_publico / len(turma_por_atividade)) if turma_por_atividade else 0
    return {
        "alunos_unicos": alunos_unicos,
        "total_publico": total_publico,
        "total_equipe": total_equipe,
        "equipe_unica": len(cpf_equipe),
        "media_part_pessoa": (total_publico / alunos_unicos) if alunos_unicos else 0,
        "razao_aluno_equipe": (total_publico / total_equipe) if total_equipe else 0,
        "turma_media": turma_media,
        "publico_por_ano": sorted(publico_por_ano.items()),
        "publico_por_coord": publico_por_coord.most_common(10),
        "recorrencia": recorrencia_dist,
        "turma_dist": turma_dist,
        "aprovado_por_tipo": _pct_tipo(aprovado_por_tipo),
        "cert_por_tipo": _pct_tipo(cert_por_tipo),
        "composicao_equipe": composicao_equipe.most_common(),
    }


def blocos_indicadores(a: dict) -> tuple[str, str]:
    """Devolve (tiles_html, secoes_html) dos indicadores para um agregado `a`."""
    tiles = "".join([
        _tile(a["alunos_unicos"], "Alunos únicos", f'{a["total_publico"]} participações'),
        _tile(f'{a["media_part_pessoa"]:.1f}', "Participações/pessoa"),
        _tile(a["equipe_unica"], "Pessoas na equipe", f'{a["total_equipe"]} vínculos'),
        _tile(f'{a["razao_aluno_equipe"]:.1f}:1', "Razão aluno:equipe"),
        _tile(f'{a["turma_media"]:.1f}', "Turma média", "público por atividade"),
    ])

    secoes = [
        _secao("Alunos atendidos por ano", _barras(a["publico_por_ano"]),
               "Alcance (participações de público) por ano de cadastro da ação."),
        _secao("Recorrência de participação", _donut(a["recorrencia"]),
               "Quantas pessoas distintas participaram de 1, 2, 3–4 ou 5+ ações."),
        _secao("Tamanho de turma (por atividade)", _donut(a["turma_dist"]),
               "Distribuição do público por atividade em faixas."),
        _secao("Top 10 coordenadores por alunos atendidos", _barras(a["publico_por_coord"]),
               "Impacto por coordenador — soma do público-alvo (≠ nº de ações)."),
        _secao("Taxa de aprovação por tipo de ação", _barras(a["aprovado_por_tipo"], unidade="%"),
               "% de participantes com situação APROVADO, por tipo."),
        _secao("Taxa de certificação por tipo de ação", _barras(a["cert_por_tipo"], unidade="%"),
               "% de participantes com certificado emitido, por tipo."),
        _secao("Composição da equipe executora", _donut(a["composicao_equipe"]),
               "Perfil dos membros de equipe por função."),
    ]
    return tiles, "".join(secoes)


def gerar_indicadores(
    consolidado_json: str | Path = "data/serra_consolidado.json",
    out_html: str | Path = "indicadores.html",
    *,
    titulo: str = "SRC/Ifes — Campus Serra · Indicadores",
) -> Path:
    a = agregar_indicadores(json.loads(Path(consolidado_json).read_text(encoding="utf-8")))
    tiles, secoes_html = blocos_indicadores(a)
    html = f"""<div class="wrap">
<header><h1>{escape(titulo)}</h1>
<p class="sub">Indicadores avançados — derivados do consolidado (ação + participações)</p></header>
<div class="tiles">{tiles}</div>
{secoes_html}
<div class="pii">Indicadores <b>agregados</b>. O CPF foi usado apenas para contar pessoas
distintas e recorrência — nenhum dado pessoal é exibido.</div>
<footer>Gerado por src-etl · {a['alunos_unicos']} alunos únicos · {a['total_publico']} participações.</footer>
</div>"""
    doc = (f"<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{escape(titulo)}</title><style>{_CSS}</style></head><body>{html}</body></html>")
    out = Path(out_html)
    out.write_text(doc, encoding="utf-8")
    return out


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="src-etl-indicadores",
                                 description="Indicadores avançados (HTML) do consolidado.")
    ap.add_argument("--consolidado", default="data/serra_consolidado.json")
    ap.add_argument("--out", default="indicadores.html")
    ap.add_argument("--titulo", default="SRC/Ifes — Campus Serra · Indicadores")
    args = ap.parse_args(argv)
    p = gerar_indicadores(args.consolidado, args.out, titulo=args.titulo)
    print(f"Indicadores gerados: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
