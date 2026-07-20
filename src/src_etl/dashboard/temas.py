"""Temas das ações de extensão a partir do TEXTO (título + resumo).

A exploração com TF-IDF + KMeans revelou ~7 temas recorrentes; aqui eles viram
REGRAS de palavra-chave (determinísticas, interpretáveis e estáveis — sem depender
de sklearn no build). Cada ação recebe o primeiro tema cuja palavra-chave casa no
título+resumo; sem casar, cai em "Outros / formação".
"""
from __future__ import annotations

import unicodedata
from collections import Counter, defaultdict


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


# ordem importa: específico -> genérico
TEMAS: list[tuple[str, list[str]]] = [
    ("Mulheres e inclusão", ["mulher", "feminin", "inclus", "diversidade", "genero", "negra", "negro"]),
    ("Captação e ingresso", ["portas abertas", "processo seletivo", "meu lugar", "pre-ifes",
                             "pre ifes", "vestibular", "ingresso", "pre iniciacao"]),
    ("Robótica e cultura maker", ["robot", "arduino", "maker", "lampex", "labmaker", "lego",
                                  "scratch", "drone", "prototip", "impressora 3d"]),
    ("Empreendedorismo e incubação", ["incuba", "empreend", "startup", "negocio", "modelo de negoc",
                                      "plano de negoc"]),
    ("Saúde e bem-estar", ["saude", "transtorno", "mental", "clinic", "nutri", "enfermag",
                           "psicolog", "bem-estar", "bem estar"]),
    ("Cultura e arte", ["cultura", "arte", "artistic", "music", "audiovisual", "croche", "bordado",
                        "artesan", "teatro", "danca", "cinema", "literatura"]),
    ("Idiomas", ["ingles", "espanhol", "idioma", "lingua", "libras"]),
    ("Ciência e divulgação", ["fisica", "quimica", "matematica", "ciencia", "olimpiada", "feira de",
                              "semana de ciencia", "astronomia", "divulgacao cientifica"]),
    ("Software, dados e sistemas", ["sistema", "software", "plataforma", "aplicativo", " app",
                                    "dados", "programacao", "computac", "web", "intelig"]),
    ("Escola e formação de professores", ["escola", "professor", "docente", "ensino fundamental",
                                          "rede municipal", "rede publica", "educacao basica"]),
]
OUTROS = "Outros / formação"


def tema_de(a: dict) -> str:
    txt = _norm((a.get("Título ação") or "") + " " + (a.get("Resumo") or ""))
    for nome, kws in TEMAS:
        if any(k in txt for k in kws):
            return nome
    return OUTROS


def _e_extensao(a: dict) -> bool:
    return "extens" in _norm(a.get("Natureza"))


def mapa_temas(cons: dict) -> dict:
    """{acao_id: tema} para as ações de extensão."""
    return {a.get("acao_id"): tema_de(a) for a in cons.get("acoes", []) if _e_extensao(a)}


def agregar_temas(cons: dict, slugs: dict | None = None) -> list[dict]:
    """Lista de temas ordenada por público, com nº de ações, coordenadores e exemplos."""
    slugs = slugs or {}
    dados: dict[str, dict] = defaultdict(
        lambda: {"acoes": 0, "publico": 0, "pset": set(), "coord": Counter(), "ex": []})
    for a in cons.get("acoes", []):
        if not _e_extensao(a):
            continue
        t = tema_de(a)
        d = dados[t]
        d["acoes"] += 1
        for p in a.get("participacoes", []):
            if (p.get("tipo") or "").startswith("Públic"):
                d["publico"] += 1                       # atendimentos (registros)
                pid = p.get("CPF") or p.get("Nome")
                if pid:
                    d["pset"].add(pid)                  # pessoas distintas
        coord = (a.get("Coordenador(a)") or "").strip()
        if coord:
            d["coord"][coord] += 1
        if len(d["ex"]) < 4:
            d["ex"].append({"titulo": (a.get("Título ação") or "—")[:60], "acao_id": a.get("acao_id")})
    out = []
    for tema, d in dados.items():
        out.append({
            "tema": tema, "acoes": d["acoes"], "publico": d["publico"], "pessoas": len(d["pset"]),
            "coordenadores": [{"nome": n, "slug": slugs.get(_norm(n)), "n": c}
                              for n, c in d["coord"].most_common(6)],
            "exemplos": d["ex"],
        })
    return sorted(out, key=lambda x: -x["publico"])


def temas_por_pessoa(cons: dict) -> dict:
    """{nome_normalizado: Counter(tema -> nº de ações)} — coord ou equipe (extensão)."""
    mapa = mapa_temas(cons)
    por: dict[str, Counter] = defaultdict(Counter)
    for a in cons.get("acoes", []):
        if not _e_extensao(a):
            continue
        t = mapa.get(a.get("acao_id"))
        if not t:
            continue
        nomes = set()
        coord = (a.get("Coordenador(a)") or "").strip()
        if coord:
            nomes.add(_norm(coord))
        for p in a.get("participacoes", []):
            if not (p.get("tipo") or "").startswith("Públic"):
                nm = (p.get("Nome") or "").strip()
                if nm:
                    nomes.add(_norm(nm))
        for n in nomes:
            por[n][t] += 1
    return por
