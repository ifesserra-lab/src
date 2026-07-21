"""Temas das ações de extensão a partir do TEXTO (título + resumo).

A exploração com TF-IDF + KMeans revelou ~7 temas recorrentes; aqui eles viram
REGRAS de palavra-chave (determinísticas, interpretáveis e estáveis — sem depender
de sklearn no build). Cada ação recebe o primeiro tema cuja palavra-chave casa no
título+resumo; sem casar, cai em "Outros / formação".
"""
from __future__ import annotations

import json
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

_CACHE_DESC = Path("data/temas_descricoes.json")


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


def _ativa(a: dict) -> bool:
    """Ação com participação registrada (público ou equipe > 0)."""
    if a.get("total_participacoes"):
        return True
    return any(p.get("Nome") or p.get("CPF") for p in a.get("participacoes", []))


def _considera(a: dict) -> bool:
    return _e_extensao(a) and _ativa(a)


def mapa_temas(cons: dict) -> dict:
    """{acao_id: tema} para as ações de extensão."""
    return {a.get("acao_id"): tema_de(a) for a in cons.get("acoes", []) if _considera(a)}


def agregar_temas(cons: dict, slugs: dict | None = None) -> list[dict]:
    """Lista de temas ordenada por público, com nº de ações, coordenadores e exemplos."""
    slugs = slugs or {}
    dados: dict[str, dict] = defaultdict(
        lambda: {"acoes": 0, "publico": 0, "pset": set(), "coord": Counter(), "ex": []})
    for a in cons.get("acoes", []):
        if not _considera(a):
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


def _cor_tipo(tipo: str) -> str:
    """Cor (token do tema) por tipo de ação — mesma semântica dos chips do site."""
    tl = (tipo or "").lower()
    return ("var(--c1)" if "curso" in tl else "var(--c3)" if "evento" in tl
            else "var(--c4)" if "projeto" in tl else "var(--c2)" if "programa" in tl
            else "var(--c5)" if ("oficina" in tl or "produto" in tl) else "var(--muted)")


def dados_treemap_tema(cons: dict) -> list[dict]:
    """Grupos para `relatorio._treemap`: tema × tipo de ação (área = atendimentos).

    Cor = tipo (identidade categórica, ordem fixa). Ordena tema e tipo por volume."""
    mat: dict[str, Counter] = defaultdict(Counter)
    for a in cons.get("acoes", []):
        if not _considera(a):
            continue
        t = tema_de(a)
        tp = (a.get("Tipo ação") or "—").strip() or "—"
        pub = sum(1 for p in a.get("participacoes", [])
                  if (p.get("tipo") or "").startswith("Públic"))
        mat[t][tp] += pub
    grupos = []
    for tema, c in mat.items():
        tiles = [(tp, v, _cor_tipo(tp)) for tp, v in c.most_common()]
        grupos.append({"nome": tema, "tiles": tiles})
    grupos.sort(key=lambda g: -sum(v for _, v, _ in g["tiles"]))
    return grupos


def payload_treemap_tema(cons: dict) -> dict:
    """Payload p/ `relatorio._treemap_interativo`: tema › tipo › iniciativa."""
    matp: dict[str, Counter] = defaultdict(Counter)
    drillmap: dict[str, list] = defaultdict(list)
    zero: dict[str, int] = defaultdict(int)
    tipos: set[str] = set()
    for a in cons.get("acoes", []):
        if not _considera(a):
            continue
        t = tema_de(a)
        tp = (a.get("Tipo ação") or "—").strip() or "—"
        tipos.add(tp)
        pub = sum(1 for p in a.get("participacoes", [])
                  if (p.get("tipo") or "").startswith("Públic"))
        matp[t][tp] += pub
        if pub > 0:
            drillmap[t].append({"t": (a.get("Título ação") or "—")[:60], "c": tp, "v": pub})
        else:
            zero[t] += 1
    groups = [{"nome": tema, "parts": [[tp, v] for tp, v in c.most_common()]}
              for tema, c in matp.items()]
    groups.sort(key=lambda g: -sum(v for _, v in g["parts"]))
    for t in drillmap:
        drillmap[t].sort(key=lambda r: -r["v"])
    return {
        "dim": "tipo", "medida": "atendimentos", "crumb_all": "Todos os temas",
        "colors": {tp: _cor_tipo(tp) for tp in tipos},
        "labels": {tp: tp for tp in tipos},
        "groups": groups, "drill": dict(drillmap), "zero": dict(zero),
    }


def _material_tema(cons: dict) -> dict:
    """{tema: [títulos + trechos de resumo dos projetos]} para alimentar o modelo."""
    mat: dict[str, dict] = defaultdict(lambda: {"titulos": [], "resumos": []})
    for a in cons.get("acoes", []):
        if not _considera(a):
            continue
        t = tema_de(a)
        tit = (a.get("Título ação") or "").strip()
        if tit and len(mat[t]["titulos"]) < 14:
            mat[t]["titulos"].append(tit)
        rs = (a.get("Resumo") or "").strip()
        if rs and len(mat[t]["resumos"]) < 3:
            mat[t]["resumos"].append(rs[:300])
    return mat


def descrever_temas(cons: dict, *, cache_path=_CACHE_DESC, modelo: str | None = None,
                    gerar: bool = False, on_progress=None) -> dict:
    """Descrição (1–2 frases) de cada tema via Mistral, com cache em disco.

    Lê o cache sempre; só chama a API quando `gerar=True` (precisa de MISTRAL_KEY).
    Baseia-se APENAS nos títulos/resumos dos projetos do tema (não inventa)."""
    log = on_progress or (lambda _m: None)
    cache_p = Path(cache_path)
    cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}
    if not gerar:
        return cache
    import httpx
    from ..etl.enriquecer import API_URL, MODELO_PADRAO, carregar_chave
    modelo = modelo or MODELO_PADRAO
    mat = _material_tema(cons)
    pend = [t for t in mat if t not in cache]
    log(f"descrições de tema: {len(cache)} em cache, {len(pend)} a gerar")
    if not pend:
        return cache
    chave = carregar_chave()
    sistema = ("Você descreve TEMAS de extensão universitária do Ifes campus Serra, em português, "
               "tom institucional. Para cada tema, escreva 1 a 2 frases explicando o que o "
               "caracteriza, com base APENAS nos títulos e resumos dos projetos listados. Não "
               "invente números, nomes ou resultados. Responda APENAS JSON.")
    usuario = ("Descreva cada tema. Formato: {\"desc\": {\"<tema>\": \"texto\"}}\n\n" + "\n\n".join(
        f"[{t}]\nProjetos: " + "; ".join(mat[t]["titulos"])
        + ("\nResumos: " + " || ".join(mat[t]["resumos"]) if mat[t]["resumos"] else "")
        for t in pend))
    body = {"model": modelo, "temperature": 0.3, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": sistema},
                         {"role": "user", "content": usuario}]}
    try:
        with httpx.Client() as cli:
            for tent in range(4):
                r = cli.post(API_URL, json=body, headers={"Authorization": f"Bearer {chave}"}, timeout=120)
                if r.status_code == 429:
                    time.sleep(2 * (tent + 1)); continue
                r.raise_for_status()
                res = json.loads(r.json()["choices"][0]["message"]["content"])
                for t, txt in (res.get("desc") or {}).items():
                    if isinstance(txt, str) and txt.strip():
                        cache[t] = txt.strip()
                break
    except Exception as e:
        log(f"  ! erro: {str(e)[:80]}")
    cache_p.parent.mkdir(parents=True, exist_ok=True)
    cache_p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  ok ({len(cache)} descrições)")
    return cache


def temas_por_pessoa(cons: dict) -> dict:
    """{nome_normalizado: Counter(tema -> nº de ações)} — coord ou equipe (extensão)."""
    mapa = mapa_temas(cons)
    por: dict[str, Counter] = defaultdict(Counter)
    for a in cons.get("acoes", []):
        if not _considera(a):
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


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="src-etl-temas",
                                 description="Temas das ações + descrição por IA (Mistral).")
    ap.add_argument("--consolidado", default="data/serra_consolidado.json")
    ap.add_argument("--descrever", action="store_true",
                    help="gera a descrição de cada tema via Mistral (precisa de MISTRAL_KEY)")
    args = ap.parse_args(argv)
    cons = json.loads(Path(args.consolidado).read_text(encoding="utf-8"))
    if args.descrever:
        descrever_temas(cons, gerar=True, on_progress=print)
    for t in agregar_temas(cons):
        print(f"{t['tema']:36} {t['acoes']:3} ações · {t['publico']:5} atend · {t['pessoas']:5} pessoas")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
