"""Visão global: programas guarda-chuva + rede de colaboração ("quem ajuda quem").

Dois olhares sobre o consolidado:
  1. Programas que agregam várias ações (campo "Ação vinculante") — ex.: LAMPEX,
     LEDS, "Ifes para todos". Mostra hubs e público agregado.
  2. Rede de colaboração entre coordenadores(as): dois são ligados quando uma
     mesma pessoa atuou na equipe de execução de ambos. Coordenadores(as) são
     dado público; os membros de equipe entram só como elo (CPF), nunca exibidos.

Reaproveita paleta/gráficos de `relatorio`.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from html import escape
from itertools import combinations
from pathlib import Path

from .relatorio import _barras, _secao, _tile


def agregar_rede(consolidado: dict) -> dict:
    acoes = consolidado.get("acoes", [])

    publico_by_proc = {}
    for a in acoes:
        publico_by_proc[a.get("Processo nº")] = sum(
            1 for p in a.get("participacoes", []) if p.get("tipo", "").startswith("Público"))

    # programas guarda-chuva — FONTE AUTORITATIVA: campo "acoes_vinculadas"
    # (buscado por acao_id em consulta-acao-vinculada), agrupado por processo do pai.
    tem_autoritativo = any(a.get("acoes_vinculadas") for a in acoes)
    programas = []          # (titulo_pai, processo_pai, n_filhos, publico_agregado)
    if tem_autoritativo:
        for a in acoes:
            filhas = a.get("acoes_vinculadas") or []
            if filhas:
                # agregado = público do PRÓPRIO programa + o das ações filhas
                pub = publico_by_proc.get(a.get("Processo nº"), 0) + sum(
                    publico_by_proc.get(fp.get("processo"), 0) for fp in filhas)
                programas.append((a.get("Título ação") or a.get("Processo nº"),
                                  a.get("Processo nº"), len(filhas), pub))
    else:
        # fallback (menos confiável): campo texto "Ação vinculante" das filhas, por processo do pai
        filhos = defaultdict(list)
        for a in acoes:
            v = (a.get("Ação vinculante") or "").strip()
            if v and v != "-":
                proc_pai = v.split(" - ", 1)[0].strip()
                filhos[(proc_pai, v.split(" - ", 1)[1].strip() if " - " in v else v)].append(
                    a.get("Processo nº"))
        for (proc_pai, tit_pai), procs in filhos.items():
            programas.append((tit_pai, proc_pai, len(procs),
                              publico_by_proc.get(proc_pai, 0)
                              + sum(publico_by_proc.get(pp, 0) for pp in procs)))
    programas.sort(key=lambda x: (-x[2], -x[3]))

    # colaboração: cpf de equipe -> conjunto de coordenadores
    cpf_coords = defaultdict(set)
    for a in acoes:
        coord = (a.get("Coordenador(a)") or "—").strip() or "—"
        for p in a.get("participacoes", []):
            if not p.get("tipo", "").startswith("Público"):
                cpf = (p.get("CPF") or "").strip()
                if cpf:
                    cpf_coords[cpf].add(coord)

    pair_w = Counter()      # (coordA, coordB) -> nº de pessoas em comum
    for coords in cpf_coords.values():
        for c1, c2 in combinations(sorted(coords), 2):
            pair_w[(c1, c2)] += 1

    grau = Counter()        # nº de parceiros distintos
    for (c1, c2) in pair_w:
        grau[c1] += 1
        grau[c2] += 1

    coord_colab = grau.most_common(10)
    top_parcerias = [(f"{c1} ↔ {c2}", w) for (c1, c2), w in pair_w.most_common(10)]

    # grafo (layout circular) dos coordenadores mais conectados
    topN = [c for c, _ in grau.most_common(14)]
    idx = {c: i for i, c in enumerate(topN)}
    edges = [(idx[c1], idx[c2], w) for (c1, c2), w in pair_w.items()
             if c1 in idx and c2 in idx]

    return {
        "n_programas": len(programas),
        "maior_programa": (programas[0][0], programas[0][2]) if programas else None,
        "n_coord_colab": len([c for c, g in grau.items() if g > 0]),
        "n_parcerias": len(pair_w),
        "programas": [(t, n) for t, _proc, n, _p in programas[:10]],
        "programas_publico": [(t, p) for t, _proc, n, p in sorted(programas, key=lambda x: -x[3])[:10] if p],
        "coord_colab": coord_colab,
        "top_parcerias": top_parcerias,
        "grafo_nodes": topN,
        "grafo_edges": edges,
    }


def _lista_pares(itens: list[tuple[str, int]], sufixo: str) -> str:
    if not itens:
        return '<p class="vazio">Sem dados.</p>'
    linhas = "".join(
        f'<div class="li"><span class="li-tit">{escape(str(t))}</span>'
        f'<span class="li-proc">{v} {sufixo}</span></div>' for t, v in itens
    )
    return f'<div class="lista">{linhas}</div>'


def _grafo(nodes: list[str], edges: list[tuple[int, int, int]]) -> str:
    """Grafo circular SVG: nós = coordenadores, arestas = pessoas em comum."""
    if len(nodes) < 2:
        return '<p class="vazio">Colaboração insuficiente para desenhar a rede.</p>'
    n = len(nodes)
    W = 620
    cx, cy, R = W / 2, 300, 210
    pos = []
    for i in range(n):
        ang = 2 * math.pi * i / n - math.pi / 2
        pos.append((cx + R * math.cos(ang), cy + R * math.sin(ang)))
    maxw = max((w for _, _, w in edges), default=1)

    arestas = []
    for i, j, w in edges:
        x1, y1 = pos[i]
        x2, y2 = pos[j]
        sw = 1 + (w / maxw) * 5
        op = 0.18 + (w / maxw) * 0.5
        arestas.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                       f'stroke="var(--series-1)" stroke-width="{sw:.1f}" stroke-opacity="{op:.2f}"/>')

    nos = []
    for i, nome in enumerate(nodes):
        x, y = pos[i]
        # rótulo: 2 primeiros nomes
        curto = " ".join(nome.split()[:2])
        anchor = "start" if x >= cx else "end"
        dx = 10 if x >= cx else -10
        nos.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="var(--series-1)" '
            f'stroke="var(--surface-1)" stroke-width="2"><title>{escape(nome)}</title></circle>'
            f'<text x="{x+dx:.0f}" y="{y+4:.0f}" text-anchor="{anchor}" class="net-lbl">{escape(curto)}</text>'
        )
    return (f'<svg viewBox="0 0 {W} 600" width="100%" role="img">'
            f'{"".join(arestas)}{"".join(nos)}</svg>')


def blocos_rede(a: dict) -> tuple[str, str]:
    """(tiles_html, secoes_html) da visão global de rede."""
    mp = a["maior_programa"]
    tiles = "".join([
        _tile(a["n_programas"], "Programas guarda-chuva", "com ações vinculadas"),
        _tile(mp[1] if mp else "—", "Maior programa", (mp[0][:22] if mp else "")),
        _tile(a["n_coord_colab"], "Coordenadores em rede"),
        _tile(a["n_parcerias"], "Parcerias (pares)"),
    ])
    secoes = [
        _secao("Programas por nº de ações vinculadas", _barras(a["programas"]),
               'Ações "guarda-chuva" que agregam outras (campo Ação vinculante) — ex.: LAMPEX, LEDS.',
               explica="No SRC, uma ação pode declarar outra como 'Ação vinculante' — isso cria "
               "programas guarda-chuva que abrigam projetos/cursos/eventos filhos. Este gráfico "
               "conta quantas ações filhas cada programa agrega, usando a consulta oficial de "
               "ações vinculadas do sistema (não o campo de texto, que é incompleto). Mede o papel "
               "estruturante do programa: quanto mais filhas, mais ele funciona como plataforma."),
        _secao("Programas por público agregado", _barras(a["programas_publico"]),
               "Público-alvo do próprio programa + das ações filhas.",
               explica="Alcance total do ecossistema de cada programa: soma o público-alvo "
               "registrado nas atividades do PRÓPRIO programa com o público de todas as suas "
               "ações filhas. Exemplo: LAMPEX = participantes das suas 117 atividades internas + "
               "participantes dos projetos vinculados a ele. Mede o impacto consolidado do "
               "programa como um todo, não apenas o que está formalmente 'dentro' dele. "
               "Base: participações (pessoas podem repetir entre atividades)."),
        _secao("Rede de colaboração entre coordenadores(as)", _grafo(a["grafo_nodes"], a["grafo_edges"]),
               "Cada elo liga dois coordenadores que compartilham uma mesma pessoa na equipe. "
               "Passe o mouse nos nós para ver os nomes.",
               explica="Grafo de 'quem ajuda quem': dois coordenadores ficam conectados quando uma "
               "mesma pessoa (identificada por CPF, nunca exibido) participou da equipe de "
               "execução de ações de ambos. Linhas mais grossas = mais pessoas em comum. Mostra "
               "os núcleos de cooperação real do campus — laboratórios e grupos que trocam "
               "bolsistas, voluntários e colaboradores. Exibe os 14 coordenadores mais conectados."),
        _secao("Coordenadores(as) mais colaborativos", _barras(a["coord_colab"]),
               "Nº de parceiros distintos (coordenadores com equipe em comum).",
               explica="Para cada coordenador(a), o número de OUTROS coordenadores com quem "
               "compartilha ao menos uma pessoa de equipe. É o 'grau' do nó na rede acima: valores "
               "altos indicam articuladores — pessoas que conectam grupos diferentes da extensão."),
        _secao("Principais parcerias", _lista_pares(a["top_parcerias"], "pessoas em comum"),
               "Pares de coordenadores com mais pessoas de equipe em comum.",
               explica="As duplas de coordenadores com maior interseção de equipe. Muitas pessoas "
               "em comum normalmente indica laboratório/grupo compartilhado ou linha de trabalho "
               "conjunta de longo prazo — parcerias estruturais, não pontuais."),
    ]
    return tiles, "".join(secoes)


def carregar(consolidado_json: str | Path = "data/serra_consolidado.json") -> dict:
    return json.loads(Path(consolidado_json).read_text(encoding="utf-8"))
