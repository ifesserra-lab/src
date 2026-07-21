"""Análise de investimento: quais iniciativas merecem aporte e quais, estando
dormentes, merecem incentivo para reativar — cruzando **nicho** (cluster temático),
**impacto** (público-alvo atendido) e **público** (aluno × comunidade), além do
**status temporal** (ativa × dormente).

Nicho = `temas.tema_de` (cluster derivado do título+resumo). É o mesmo conceito de
nicho já usado na página Temas e, ao contrário da área temática oficial (vazia em
boa parte do cadastro recente), classifica todas as iniciativas — sem "—".

Status (relativo ao ano de referência, hoje):
  • ativa ........ última atividade registrada há ≤ 2 anos  (>= REF-2)
  • dormente ..... última atividade há ≥ 5 anos            (<= REF-5)
  • intermediária. entre 3 e 4 anos                        (REF-4 .. REF-3)

Ano da última atividade = maior ano encontrado em Data de cadastro, Data último
relatório e nas datas de Início/Término das participações.

RESSALVA DE IMPACTO (ver `limites_impacto` / nota na página):
o indicador de público conta **registros de participação**. Iniciativas cujo
alcance não passa por lista de inscrição — plataformas, serviços de abrangência
estadual, ferramentas digitais, eventos de público aberto (ex.: ConectaFapes, que
atende pesquisadores de todo o estado) — ficam **subestimadas**. Para essas, o
impacto real precisa vir de outra fonte (relatórios finais, métricas de plataforma,
nº de instituições/municípios atendidos). Não somar "maçã com laranja".

CLI:  src-etl-investimento --consolidado data/serra_consolidado.json --out investimento.json
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

from .temas import tema_de

# ano de referência = ano corrente (define a régua de ativa/dormente)
ANO_REF = datetime.now().year
ATIVA_DESDE = ANO_REF - 2       # última atividade >= este ano  -> ativa
DORMENTE_ATE = ANO_REF - 5      # última atividade <= este ano  -> dormente

_ANO = re.compile(r"/(\d{4})\b")


def _anos(a: dict) -> set[int]:
    """Todos os anos citados na ação (cadastro, relatório, início/término das partes)."""
    ys: set[int] = set()
    for campo in ("Data de cadastro", "Data último relatório"):
        m = _ANO.search(str(a.get(campo) or ""))
        if m:
            ys.add(int(m.group(1)))
    for p in a.get("participacoes", []):
        for campo in ("Início", "Término"):
            m = _ANO.search(str(p.get(campo) or ""))
            if m:
                ys.add(int(m.group(1)))
    return ys


def _publico(a: dict) -> int:
    """Registros de público-alvo (atendimentos). Ver ressalva de impacto no módulo."""
    return sum(1 for p in a.get("participacoes", [])
               if (p.get("tipo") or "").startswith("Públic"))


def _status(ultimo: int) -> str:
    if ultimo and ultimo >= ATIVA_DESDE:
        return "ativa"
    if ultimo and ultimo <= DORMENTE_ATE:
        return "dormente"
    return "intermediaria"


# ---- recomendações curadas (narrativa da análise, ancorada nos dados) ----
_RECOMENDACOES = [
    {
        "grupo": "Investir e escalar",
        "cor": "ok",
        "descricao": "Ativas, alto público, fomento já engatado. Concentrar recurso aqui "
                     "= maior retorno por real.",
        "exemplos": ["LAMPEX — Laboratório Modelo de Práticas (motor tecnológico, maior público)",
                     "Ecossistema maker: LabMaker Serra, LabMaker 4.0, Conectando Talentos (Robótica)",
                     "Núcleo Incubador Serra (empreendedorismo)",
                     "Inclusão: Semana de Educação Especial + Atividades físicas adaptadas"],
    },
    {
        "grupo": "Reativar com incentivo",
        "cor": "cta",
        "descricao": "Dormentes de público comprovadamente grande e baixo custo de retomada. "
                     "Melhor relação impacto/esforço para reanimar.",
        "exemplos": ["Ifes Portas Abertas (maior alcance parado; alinha captação de alunos)",
                     "Física ao Alcance de Todos",
                     "Tutoria de Estudos Orientados",
                     "Semana de Controle e Automação (reabrir como braço de eventos do LAMPEX)"],
    },
    {
        "grupo": "Expandir nicho subatendido",
        "cor": "s1",
        "descricao": "Nichos com público baixo e poucas ativas — espaço em branco para "
                     "novas iniciativas.",
        "exemplos": ["Saúde e bem-estar (só tração via atividades adaptadas)",
                     "Meio ambiente (Química Verde já abre a trilha)",
                     "Idiomas (público-alvo praticamente não registrado)"],
    },
    {
        "grupo": "Depende de fomento externo",
        "cor": "warn",
        "descricao": "Alto impacto social para a comunidade não-aluna, mas presas a convênio "
                     "que expirou. Reativação condicionada a novo edital (PRONATEC/SETEC).",
        "exemplos": ["Curso de Auxiliar Administrativo (PRONATEC)",
                     "Curso de Operador de Computador (PRONATEC)",
                     "Mulheres Mil — Eletricista Instalador Predial"],
    },
]

# ---- limite do indicador de público: impacto difuso / não-contável ----
_LIMITES_IMPACTO = {
    "texto": (
        "O indicador de público conta <b>registros de participação</b> (listas de "
        "inscrição/certificação). Há iniciativas cujo alcance <b>não passa por lista</b> e "
        "por isso aparecem <b>subestimadas</b> ou zeradas: plataformas e ferramentas digitais, "
        "serviços de abrangência estadual, e eventos de público aberto. "
        "Exemplo: <b>ConectaFapes</b> — plataforma de apoio a pesquisadores de <b>todo o "
        "estado</b>; o número de inscritos não reflete o alcance real."),
    "sugestoes": [
        {"titulo": "Ler os relatórios finais/anuais",
         "detalhe": "Extrair dos relatórios (temos os .odt no acervo) os números que a equipe "
                    "declara — beneficiários alcançados, nº de eventos, público estimado, "
                    "resultados qualitativos. Dá para automatizar com extração por IA/NLP sobre "
                    "os relatórios já coletados."},
        {"titulo": "Métricas de plataforma (projetos digitais)",
         "detalhe": "Para ConectaFapes e similares: usuários cadastrados, acessos, downloads, "
                    "pesquisadores/editais apoiados — puxados do próprio sistema."},
        {"titulo": "Indicadores indiretos de abrangência",
         "detalhe": "Nº de instituições, municípios ou regiões atendidas; parcerias firmadas. "
                    "Mede espalhamento quando a contagem de pessoas não cabe."},
        {"titulo": "Campo estruturado de alcance estimado",
         "detalhe": "Pedir no cadastro/relatório um 'alcance estimado' com método declarado — "
                    "vira dado comparável sem depender de raspagem posterior."},
        {"titulo": "Classificar por tipo de impacto",
         "detalhe": "Marcar cada iniciativa como impacto direto-contável × difuso/plataforma. "
                    "Não somar os dois no mesmo total — ranquear dentro de cada classe."},
    ],
    "exemplos_subestimados": ["ConectaFapes (plataforma estadual de pesquisa)"],
}


def agregar_investimento(cons: dict, *, top: int = 12) -> dict:
    """Agrega a análise de investimento. Estrutura pronta para servir como JSON aberto."""
    linhas: list[dict] = []
    for a in cons.get("acoes", []):
        ys = _anos(a)
        ultimo = max(ys) if ys else 0
        linhas.append({
            "acao_id": a.get("acao_id"),
            "titulo": (a.get("Título ação") or "—").strip(),
            "nicho": tema_de(a),
            "tipo": a.get("Tipo ação"),
            "natureza": a.get("Natureza"),
            "fomento": a.get("Fomento"),
            "coordenador": (a.get("Coordenador(a)") or "").strip(),
            "publico": _publico(a),
            "participacoes": a.get("total_participacoes", 0),
            "ano_ultima": ultimo or None,
            "status": _status(ultimo),
            "url": f"acoes/{a.get('acao_id')}.html",
        })

    # por nicho × status
    nicho: dict[str, dict] = defaultdict(
        lambda: {"iniciativas": 0, "publico": 0, "ativas": 0, "publico_ativo": 0,
                 "dormentes": 0, "publico_dormente": 0, "intermediarias": 0})
    for r in linhas:
        d = nicho[r["nicho"]]
        d["iniciativas"] += 1
        d["publico"] += r["publico"]
        if r["status"] == "ativa":
            d["ativas"] += 1
            d["publico_ativo"] += r["publico"]
        elif r["status"] == "dormente":
            d["dormentes"] += 1
            d["publico_dormente"] += r["publico"]
        else:
            d["intermediarias"] += 1
    por_nicho = [{"nicho": k, **v} for k, v in nicho.items()]
    por_nicho.sort(key=lambda x: -x["publico"])

    def _mag(r):  # colunas enxutas para as tabelas/JSON de destaque
        return {k: r[k] for k in ("acao_id", "titulo", "nicho", "tipo", "natureza",
                                  "fomento", "publico", "ano_ultima", "url")}

    ativas = sorted((r for r in linhas if r["status"] == "ativa"),
                    key=lambda x: -x["publico"])
    dormentes = sorted((r for r in linhas if r["status"] == "dormente"),
                       key=lambda x: -x["publico"])

    totais = {
        "iniciativas": len(linhas),
        "publico": sum(r["publico"] for r in linhas),
        "participacoes": sum(r["participacoes"] for r in linhas),
        "ativas": sum(1 for r in linhas if r["status"] == "ativa"),
        "dormentes": sum(1 for r in linhas if r["status"] == "dormente"),
        "intermediarias": sum(1 for r in linhas if r["status"] == "intermediaria"),
    }
    return {
        "ano_referencia": ANO_REF,
        "criterio_status": {
            "ativa": f"última atividade >= {ATIVA_DESDE}",
            "intermediaria": f"{DORMENTE_ATE + 1}–{ATIVA_DESDE - 1}",
            "dormente": f"última atividade <= {DORMENTE_ATE}",
        },
        "nicho_definicao": "cluster temático derivado do título+resumo (temas.tema_de)",
        "impacto_definicao": "registros de público-alvo (atendimentos)",
        "totais": totais,
        "por_nicho": por_nicho,
        "top_ativas": [_mag(r) for r in ativas[:top]],
        "top_dormentes": [_mag(r) for r in dormentes[:top]],
        "recomendacoes": _RECOMENDACOES,
        "limites_impacto": _LIMITES_IMPACTO,
        "iniciativas": linhas,
    }


# --------------------------------------------------------------- blocos HTML
def _fmt(v) -> str:
    return f"{v:,}".replace(",", ".")


def _tabela_destaque(itens: list[dict], *, cta_col: str) -> str:
    """Tabela de iniciativas em destaque (ativas ou dormentes)."""
    if not itens:
        return '<p class="vazio">Sem dados.</p>'
    rows = "".join(
        f'<tr><td><a class="lk" href="{r["url"]}">{escape(r["titulo"])}</a></td>'
        f'<td>{escape(r["nicho"])}</td>'
        f'<td><span class="badge">{escape(r["tipo"] or "—")}</span></td>'
        f'<td class="ja-num">{_fmt(r["publico"])}</td>'
        f'<td class="ja-num">{r["ano_ultima"] or "—"}</td>'
        f'<td>{escape((r["fomento"] or "—"))}</td></tr>'
        for r in itens)
    return (f'<div class="card" style="margin-top:14px;overflow:auto"><table class="tb">'
            f'<tr><th>Iniciativa</th><th>Nicho</th><th>Tipo</th>'
            f'<th>{escape(cta_col)}</th><th>Últ. atividade</th><th>Fomento</th></tr>'
            f'{rows}</table></div>')


def tabela_ativas(a: dict) -> str:
    return _tabela_destaque(a["top_ativas"], cta_col="Público")


def tabela_dormentes(a: dict) -> str:
    return _tabela_destaque(a["top_dormentes"], cta_col="Público (pico)")


def dados_treemap_nicho(a: dict) -> list[dict]:
    """Grupos para `relatorio._treemap`: nicho × status (área = público).

    Cor = estado temporal (verde ativa · laranja dormente · cinza intermediária).
    'intermediária' = público que não é nem de ativa nem de dormente."""
    grupos = []
    for n in a["por_nicho"]:
        meio = max(0, n["publico"] - n["publico_ativo"] - n["publico_dormente"])
        grupos.append({"nome": n["nicho"], "tiles": [
            ("ativa", n["publico_ativo"], "var(--ok)"),
            ("dormente", n["publico_dormente"], "var(--cta)"),
            ("intermediária", meio, "var(--muted)"),
        ]})
    return grupos


def payload_treemap_nicho(a: dict) -> dict:
    """Payload p/ `relatorio._treemap_interativo`: nicho › status › iniciativa."""
    from collections import defaultdict
    groups = []
    for n in a["por_nicho"]:
        meio = max(0, n["publico"] - n["publico_ativo"] - n["publico_dormente"])
        groups.append({"nome": n["nicho"], "parts": [
            ["ativa", n["publico_ativo"]], ["dormente", n["publico_dormente"]],
            ["intermediaria", meio]]})
    dd: dict[str, list] = defaultdict(list)
    for r in a["iniciativas"]:
        dd[r["nicho"]].append(r)
    drill, zero = {}, {}
    for nicho, rows in dd.items():
        rows.sort(key=lambda r: -r["publico"])
        drill[nicho] = [{"t": (r["titulo"] or "—")[:60], "c": r["status"], "v": r["publico"]}
                        for r in rows if r["publico"] > 0]
        zero[nicho] = sum(1 for r in rows if r["publico"] == 0)
    return {
        "dim": "status", "medida": "público", "crumb_all": "Todos os nichos",
        "colors": {"ativa": "var(--ok)", "dormente": "var(--cta)", "intermediaria": "var(--muted)"},
        "labels": {"ativa": "ativa", "dormente": "dormente", "intermediaria": "intermediária"},
        "groups": groups, "drill": drill, "zero": zero,
    }


def tabela_nicho(a: dict) -> str:
    """Nicho × status: público total, ativas vs dormentes."""
    rows = "".join(
        f'<tr><td>{escape(n["nicho"])}</td>'
        f'<td class="ja-num">{n["iniciativas"]}</td>'
        f'<td class="ja-num">{_fmt(n["publico"])}</td>'
        f'<td class="ja-num">{n["ativas"]} · {_fmt(n["publico_ativo"])}</td>'
        f'<td class="ja-num">{n["dormentes"]} · {_fmt(n["publico_dormente"])}</td>'
        f'<td class="ja-num">{n["intermediarias"]}</td></tr>'
        for n in a["por_nicho"])
    return (f'<div class="card" style="margin-top:14px;overflow:auto"><table class="tb">'
            f'<tr><th>Nicho</th><th>Ações</th><th>Público</th>'
            f'<th>Ativas (n·púb)</th><th>Dormentes (n·púb)</th><th>Meio</th></tr>'
            f'{rows}</table></div>')


_REC_COR = {"ok": "#01B574", "cta": "#f97316", "s1": "#3b82f6", "warn": "#eda100"}


def cards_recomendacoes(a: dict) -> str:
    cards = []
    for r in a["recomendacoes"]:
        cor = _REC_COR.get(r.get("cor"), "var(--series-1)")
        exs = "".join(f"<li>{escape(x)}</li>" for x in r["exemplos"])
        cards.append(
            f'<div class="card" style="margin-top:14px;border-left:3px solid {cor}">'
            f'<h2 style="margin-top:0">{escape(r["grupo"])}</h2>'
            f'<p class="sec-desc" style="margin:0 0 8px">{escape(r["descricao"])}</p>'
            f'<ul style="margin:0 0 0 18px;font-size:13.5px;line-height:1.6">{exs}</ul></div>')
    return "".join(cards)


def nota_limites(a: dict) -> str:
    """Nota de comentários: impacto difuso/não-contável e como estimar."""
    lim = a["limites_impacto"]
    sug = "".join(
        f'<li><b>{escape(s["titulo"])}.</b> {escape(s["detalhe"])}</li>'
        for s in lim["sugestoes"])
    return (
        '<div class="card" style="margin-top:14px;border-left:3px solid var(--cta)">'
        '<h2 style="margin-top:0">Nota: impacto que o número de público não captura</h2>'
        f'<p class="sec-desc" style="line-height:1.6">{lim["texto"]}</p>'
        '<p class="sec-desc" style="margin:10px 0 4px"><b>Como medir esse impacto:</b></p>'
        f'<ul style="margin:0 0 0 18px;font-size:13.5px;line-height:1.65">{sug}</ul></div>')


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(
        prog="src-etl-investimento",
        description="Análise de investimento (nicho × impacto × status) em JSON.")
    ap.add_argument("--consolidado", default="data/serra_consolidado.json")
    ap.add_argument("--out", default="investimento.json")
    args = ap.parse_args(argv)
    cons = json.loads(Path(args.consolidado).read_text(encoding="utf-8"))
    a = agregar_investimento(cons)
    Path(args.out).write_text(
        json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    t = a["totais"]
    print(f"investimento: {t['iniciativas']} iniciativas · {t['ativas']} ativas · "
          f"{t['dormentes']} dormentes -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
