"""Índice de Extensão nas 5 dimensões do FORPROEX (Indicadores Brasileiros de
Extensão Universitária, 2017) — versão para o painel do SRC.

Reaproveita os mesmos números do relatório da diretoria, calculados a partir do
consolidado do SRC. A dimensão Produção Acadêmica (cruzamento com pesquisa) só é
preenchida quando o CSV do Horizon (`por_coordenador.csv`) está disponível.
"""
from __future__ import annotations

import csv
import glob
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

from .relatorio import _barras, _secao, _tile


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def _d(s):
    try:
        return datetime.strptime((s or "").strip(), "%d/%m/%Y")
    except (ValueError, AttributeError):
        return None


def agregar_forproex(cons: dict, *, formandos_dir: str | Path = "data/formandos",
                     por_coordenador: str | Path | None = None) -> dict:
    acoes = cons.get("acoes", [])
    tot = len(acoes)
    aprov = sum(1 for a in acoes if (a.get("Relatório aprovado") or "").strip().lower() == "sim")
    com_part = sum(1 for a in acoes if a.get("total_participacoes", 0) > 0)
    programas = sum(1 for a in acoes if "programa" in _norm(a.get("Tipo ação")))

    eq: dict[str, str] = {}
    pub: dict[str, int | None] = {}
    atend = 0
    for a in acoes:
        for p in a.get("participacoes", []):
            if (p.get("tipo") or "").startswith("Públic"):
                atend += 1
                pid = p.get("CPF") or p.get("Nome")
                if pid and pid not in pub:
                    nb, i = _d(p.get("Nasc.")), _d(p.get("Início"))
                    pub[pid] = (i.year - nb.year) if (nb and i) else None
            else:
                nm = (p.get("Nome") or "").strip()
                if nm:
                    eq.setdefault(nm, p.get("Vínculo") or "")
    teq = len(eq)
    disc = sum(1 for v in eq.values() if _norm(v) == "aluno")
    serv = sum(1 for v in eq.values() if _norm(v) == "servidor")
    conv = sum(1 for v in eq.values() if _norm(v) == "convidado")
    idades = [v for v in pub.values() if v is not None]
    preuni = sum(1 for x in idades if x < 18)

    # formados alcançados como público (por nome)
    form = {}
    try:
        import openpyxl
        for f in glob.glob(str(Path(formandos_dir) / "formados_*.xlsx")):
            ws = openpyxl.load_workbook(f, read_only=True).active
            it = ws.iter_rows(values_only=True); next(it, None)
            for r in it:
                if r and r[0] and re.match(r"^(\d{4})(\d)", str(r[0]).strip()):
                    form.setdefault(_norm(r[1]), 1)
    except Exception:
        form = {}
    pub_nomes = {_norm(p.get("Nome")) for a in acoes for p in a.get("participacoes", [])
                 if (p.get("tipo") or "").startswith("Públic") and p.get("Nome")}
    form_alc = len(pub_nomes & set(form)) if form else 0

    # produção acadêmica (opcional — Horizon)
    prod = None
    pc = por_coordenador
    if pc is None:
        cand = Path("../horizon/horizon_etl/output/por_coordenador.csv")
        pc = cand if cand.exists() else None
    if pc and Path(pc).exists():
        res = {}
        with open(pc) as fh:
            for row in csv.DictReader(fh):
                res[_norm(row["coordenador_norm"])] = float(row.get("fwci") or 0)
        ext_nomes = set()
        for a in acoes:
            if "extens" in _norm(a.get("Natureza")):
                if a.get("Coordenador(a)"):
                    ext_nomes.add(_norm(a["Coordenador(a)"]))
                for p in a.get("participacoes", []):
                    if not (p.get("tipo") or "").startswith("Públic") and p.get("Nome"):
                        ext_nomes.add(_norm(p["Nome"]))
        inter = set(res) & ext_nomes
        import statistics
        prod = {"coord": len(res), "com_ext": len(inter),
                "fwci": statistics.median([res[n] for n in inter]) if inter else 0}

    return {"tot": tot, "aprov": aprov, "com_part": com_part, "pend": tot - aprov,
            "programas": programas, "teq": teq, "disc": disc, "serv": serv, "conv": conv,
            "form_alc": form_alc, "n_form": len(form), "npub": len(pub), "atend": atend,
            "preuni": preuni, "n_idade": len(idades), "prod": prod}


def blocos_forproex(a: dict) -> tuple[str, str]:
    pct = lambda x, y: f"{x/y*100:.0f}%" if y else "—"
    tiles = (
        _tile(pct(a["aprov"], a["tot"]), "Relatório aprovado", f"{a['aprov']}/{a['tot']} ações")
        + _tile(f"{a['disc']/a['teq']*100:.0f}%" if a["teq"] else "—", "Protagonismo discente",
                f"{a['disc']}/{a['teq']} na equipe")
        + _tile(pct(a["form_alc"], a["n_form"]), "Formados alcançados", f"{a['form_alc']}/{a['n_form']}")
        + _tile(f"{a['npub']:,}".replace(",", "."), "Pessoas atingidas", "público-alvo distinto")
        + _tile(f"{a['preuni']/a['n_idade']*100:.0f}%" if a["n_idade"] else "—",
                "Público < 18 anos", "pré-universitário"))

    secoes = [
        _secao("1 · Política de Gestão",
               _barras([("Relatório aprovado", a["aprov"]), ("Pendências de relatório", a["pend"]),
                        ("Com participação", a["com_part"])]),
               "Registro e conclusão formal do ciclo das ações.",
               explica="Capacidade de registrar, acompanhar e concluir as ações no SRC. "
               f"{a['aprov']} de {a['tot']} ações têm relatório final aprovado; {a['pend']} pendentes."),
        _secao("2 · Infraestrutura",
               f'<p class="vazio" style="font-size:14px">{a["programas"]} programas (iniciativas contínuas '
               'guarda-chuva). Orçamento, espaços e editais não estão no SRC — lacuna desta dimensão.</p>',
               "Estruturas permanentes de extensão (proxy: programas)."),
        _secao("3 · Política Acadêmica — protagonismo e formação",
               _barras([("Discente (aluno)", a["disc"]), ("Servidor", a["serv"]),
                        ("Convidado (externo)", a["conv"])]),
               f'Equipe executora por vínculo · {a["form_alc"]} de {a["n_form"]} formados passaram pela extensão.',
               explica="Quem executa a extensão (protagonismo estudantil) e como ela toca a formação: "
               f"{a['disc']} dos {a['teq']} membros de equipe são discentes."),
        _secao("4 · Relação Universidade-Sociedade",
               _barras([("Pessoas atingidas (distintas)", a["npub"]),
                        ("Atendimentos (participações)", a["atend"]),
                        ("Público < 18 anos", a["preuni"])]),
               "Alcance e perfil do público.",
               explica="Alcance da extensão. Falta a satisfação/percepção da comunidade e a mudança "
               "social pós-ação — núcleo desta dimensão segundo a literatura (coleta a implementar)."),
    ]
    if a["prod"]:
        p = a["prod"]
        secoes.append(_secao(
            "5 · Produção Acadêmica (extensão × pesquisa)",
            _barras([("Coord. pesquisa", p["coord"]), ("...que fazem extensão", p["com_ext"])]),
            f'FWCI mediano dos extensionistas-pesquisadores: {p["fwci"]:.2f} (acima da média mundial se >1).',
            explica="Cruzamento com o Horizon (FAPES/FACTO/Lattes/OpenAlex). FWCI/citações medem "
            "impacto CIENTÍFICO — entram como associação, não como impacto de extensão."))
    else:
        secoes.append(_secao(
            "5 · Produção Acadêmica (extensão × pesquisa)",
            '<p class="vazio" style="font-size:14px">Cruzamento com pesquisa disponível no relatório '
            'da diretoria (Horizon).</p>', "Extensão × pesquisa."))
    return tiles, "".join(secoes)
