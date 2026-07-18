"""Páginas de extensionistas: quem coordenou ou atuou na equipe de ações de Extensão.

Para cada extensionista gera uma página com as ações que coordenou e as que
participou (equipe de execução), e um resumo em linguagem natural gerado pelo
Mistral (em lote, com cache — não regera o que já existe).

Definição: extensionista = coordenador(a) OU membro de equipe executora de ação
de natureza Extensão. Público-alvo (pessoa atendida) não entra.

Privacidade: nomes de coordenadores e equipe são crédito público de execução;
CPF é usado apenas internamente para deduplicar — nunca publicado.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

import httpx

from ..etl.enriquecer import API_URL, MODELO_PADRAO, carregar_chave

_CACHE_PADRAO = Path("data/extensionistas_resumos.json")


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def _slug(nome: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", _norm(nome)).strip("-")
    return s or "pessoa"


# ------------------------------------------------------------------- coleta
def coletar_extensionistas(consolidado: dict) -> list[dict]:
    """Extrai extensionistas (coordenadores + equipe) das ações de Extensão."""
    pessoas: dict[str, dict] = {}   # chave = nome normalizado

    def _pega(nome: str) -> dict:
        k = _norm(nome)
        if k not in pessoas:
            pessoas[k] = {"nome": nome.strip(), "coordena": [], "participa": [],
                          "atividades": [], "funcoes": set(), "anos": set()}
        return pessoas[k]

    for a in consolidado.get("acoes", []):
        if "extens" not in _norm(a.get("Natureza")):
            continue
        # pessoas impactadas = público-alvo DISTINTO (CPF é só p/ deduplicar).
        # nível da ação (p/ coordenação) e por atividade (p/ quem atuou na equipe).
        pub_por_ativ: dict[str, set] = defaultdict(set)
        pub_acao: set = set()
        for part in a.get("participacoes", []):
            if (part.get("tipo") or "").startswith("Públic"):
                pid = part.get("CPF") or part.get("Nome")
                pub_acao.add(pid)
                pub_por_ativ[str(part.get("atividade_id"))].add(pid)
        pub = len(pub_acao)
        ref = {"acao_id": a.get("acao_id"), "titulo": a.get("Título ação") or "—",
               "tipo": a.get("Tipo ação") or "—", "ano": (a.get("Data de cadastro") or "")[-4:],
               "n": a.get("total_participacoes", 0), "pub": pub}
        coord = (a.get("Coordenador(a)") or "").strip()
        if coord:
            p = _pega(coord)
            p["coordena"].append(ref)
            p["anos"].add(ref["ano"])
        vistos_nesta_acao: dict[str, set] = defaultdict(set)
        ativ_nesta_acao: dict[str, set] = defaultdict(set)   # nome -> {atividade_id} realmente atuadas
        for part in a.get("participacoes", []):
            if part.get("tipo", "").startswith("Público"):
                continue
            nome = (part.get("Nome") or "").strip()
            if not nome:
                continue
            vistos_nesta_acao[nome].add((part.get("Função") or "—").strip())
            aid = part.get("atividade_id")
            if aid:
                ativ_nesta_acao[nome].add(str(aid))
        for nome, funcoes in vistos_nesta_acao.items():
            p = _pega(nome)
            p["participa"].append({**ref, "funcoes": sorted(funcoes)})
            p["funcoes"] |= funcoes
            p["anos"].add(ref["ano"])
            for aid in ativ_nesta_acao[nome]:
                p["atividades"].append({"ano": ref["ano"], "atividade_id": aid,
                                        "acao_id": ref["acao_id"],
                                        "pub": len(pub_por_ativ.get(aid, ()))})

    out = []
    slugs: dict[str, int] = {}  # noqa: reaproveitado abaixo como contador de slug
    for k in sorted(pessoas, key=lambda x: pessoas[x]["nome"]):
        p = pessoas[k]
        s = _slug(p["nome"])
        if s in slugs:      # colisão de nome -> sufixo
            slugs[s] += 1
            s = f"{s}-{slugs[s]}"
        else:
            slugs[s] = 1
        p["slug"] = s
        p["funcoes"] = sorted(p["funcoes"])
        p["anos"] = sorted(x for x in p["anos"] if x)
        out.append(p)
    return out


def coautoria(consolidado: dict) -> dict[str, Counter]:
    """{nome_normalizado: Counter(nome_colaborador -> nº de ações em comum)}.

    Dois nomes colaboram quando aparecem juntos na coordenação/equipe de uma
    mesma ação de Extensão (público-alvo NÃO conta)."""
    co: dict[str, Counter] = defaultdict(Counter)
    for a in consolidado.get("acoes", []):
        if "extens" not in _norm(a.get("Natureza")):
            continue
        # pessoas da ação: coordenador + equipe (nome canônico)
        nomes: dict[str, str] = {}   # norm -> nome exibição
        coord = (a.get("Coordenador(a)") or "").strip()
        if coord:
            nomes[_norm(coord)] = coord
        for p in a.get("participacoes", []):
            if not p.get("tipo", "").startswith("Público"):
                nm = (p.get("Nome") or "").strip()
                if nm:
                    nomes.setdefault(_norm(nm), nm)
        chaves = list(nomes)
        for i, n1 in enumerate(chaves):
            for n2 in chaves[i + 1:]:
                co[n1][nomes[n2]] += 1
                co[n2][nomes[n1]] += 1
    return co


# ------------------------------------------------------------------- resumos IA
def _material(p: dict) -> str:
    """Material factual entregue ao modelo para resumir uma pessoa."""
    linhas = [f"Nome: {p['nome']}"]
    if p["coordena"]:
        linhas.append("Coordenou: " + "; ".join(
            f"{r['titulo']} ({r['tipo']}, {r['ano']})" for r in p["coordena"][:10]))
    if p["participa"]:
        linhas.append("Participou da equipe: " + "; ".join(
            f"{r['titulo']} ({', '.join(r['funcoes'])}, {r['ano']})" for r in p["participa"][:10]))
    return "\n".join(linhas)


def gerar_resumos(pessoas: list[dict], *, cache_path: str | Path = _CACHE_PADRAO,
                  modelo: str = MODELO_PADRAO, lote: int = 8, on_progress=None) -> dict[str, str]:
    """Resumo 2–3 frases por pessoa via Mistral, em lotes, com cache em disco."""
    log = on_progress or (lambda _m: None)
    cache_p = Path(cache_path)
    cache: dict[str, str] = {}
    if cache_p.exists():
        cache = json.loads(cache_p.read_text(encoding="utf-8"))

    pendentes = [p for p in pessoas if p["slug"] not in cache]
    log(f"resumos: {len(cache)} em cache, {len(pendentes)} a gerar")
    if not pendentes:
        return cache

    chave = carregar_chave()
    sistema = ("Você escreve microbiografias institucionais de extensionistas do Ifes campus "
               "Serra, em português, tom respeitoso e factual. Para cada pessoa, escreva 2 a 3 "
               "frases resumindo sua atuação na extensão com base APENAS nos dados fornecidos "
               "(ações coordenadas, participações em equipe, funções, anos). Não invente fatos, "
               "títulos acadêmicos nem departamentos. Responda APENAS JSON.")
    with httpx.Client() as cli:
        for i in range(0, len(pendentes), lote):
            grupo = pendentes[i:i + lote]
            usuario = ("Resuma cada pessoa. Formato: {\"resumos\": {\"<slug>\": \"texto\"}}\n\n"
                       + "\n\n".join(f"[{p['slug']}]\n{_material(p)}" for p in grupo))
            body = {"model": modelo, "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": sistema},
                                 {"role": "user", "content": usuario}]}
            try:
                for tent in range(4):
                    r = cli.post(API_URL, json=body,
                                 headers={"Authorization": f"Bearer {chave}"}, timeout=90)
                    if r.status_code == 429:
                        time.sleep(2 * (tent + 1))
                        continue
                    r.raise_for_status()
                    res = json.loads(r.json()["choices"][0]["message"]["content"])
                    for slug, txt in (res.get("resumos") or {}).items():
                        if isinstance(txt, str) and txt.strip():
                            cache[slug] = txt.strip()
                    break
            except Exception as e:
                log(f"  ! lote {i//lote}: {str(e)[:70]}")
            cache_p.parent.mkdir(parents=True, exist_ok=True)
            cache_p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"  lote {i//lote + 1}/{(len(pendentes)+lote-1)//lote} ok ({len(cache)} resumos)")
            time.sleep(0.4)
    return cache
