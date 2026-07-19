"""Gera o Relatório de Ação de Extensão (modelo oficial PROEX, .odt) pré-preenchido
com os dados do SRC, para cada ação — em especial as pendentes de relatório.

O modelo oficial (Orientação Normativa CAEx 01-2020) é uma tabela `rótulo → célula
de valor`. Para cada rótulo conhecido escrevemos o valor na célula-alvo; os campos
que o SRC não possui (municípios, vulnerabilidade, parcerias, público interno
detalhado, textos descritivos) ficam em branco para o(a) coordenador(a) completar.

Privacidade: o .odt gerado contém apenas título, coordenador(a) (crédito público),
datas, área temática e CONTAGENS (público externo, equipe). Nunca CPF, e-mail ou
nomes de alunos.

Conversão para PDF: use `converter_pdf()` (precisa do LibreOffice/soffice). No site,
o PDF é gerado no CI a partir dos .odt commitados (sem tocar nos dados locais).

CLI:  src-etl-relatorio-odt --consolidado data/serra_consolidado.json --out docs
"""
from __future__ import annotations

import re
import shutil
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path

MODELO = Path(__file__).parent / "assets" / "relatorio_modelo.odt"
AREAS = ["Comunicação", "Cultura", "Direitos Humanos e Justiça", "Educação",
         "Tecnologia e Produção", "Trabalho", "Meio Ambiente", "Saúde"]


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def _data(s):
    try:
        return datetime.strptime((s or "").strip(), "%d/%m/%Y")
    except (ValueError, AttributeError):
        return None


def dados_acao(a: dict) -> dict:
    """Extrai do SRC o que dá para preencher no relatório (só contagens/atributos)."""
    pub, eq = set(), set()
    inis, terms = [], []
    for p in a.get("participacoes", []):
        i, t = _data(p.get("Início")), _data(p.get("Término"))
        if i:
            inis.append(i)
        if t:
            terms.append(t)
        if (p.get("tipo") or "").startswith("Públic"):
            pid = p.get("CPF") or p.get("Nome")
            if pid:
                pub.add(pid)
        else:
            nm = (p.get("Nome") or "").strip()
            if nm:
                eq.add(nm)
    return {
        "titulo": a.get("Título ação") or "",
        "coordenador": (a.get("Coordenador(a)") or "").strip(),
        "inicio": min(inis).strftime("%d/%m/%Y") if inis else "",
        "termino": max(terms).strftime("%d/%m/%Y") if terms else "",
        "publico_externo": len(pub),
        "equipe": len(eq),
        "area": (a.get("Área temática principal")
                 or a.get("Área temática principal (inferida)") or "").strip(),
        "final": (a.get("Relatório aprovado") or "").strip().lower() == "sim",
    }


def _preencher_doc(a: dict, saida: Path) -> dict:
    from odf.opendocument import load
    from odf.table import Table, TableRow, TableCell
    from odf.text import P
    from odf import teletype

    def set_cell(cell, texto):
        for ch in list(cell.childNodes):
            cell.removeChild(ch)
        cell.addElement(P(text=str(texto)))

    d = dados_acao(a)
    doc = load(str(MODELO))
    dt = 0
    for tab in doc.getElementsByType(Table):
        for row in tab.getElementsByType(TableRow):
            cells = row.getElementsByType(TableCell)
            txts = [teletype.extractText(c).strip() for c in cells]
            for i, t in enumerate(txts):
                tn = _norm(t)
                if tn.startswith("titulo da acao") and i + 1 < len(cells) and not txts[i + 1]:
                    set_cell(cells[i + 1], d["titulo"])
                elif tn.startswith("nome do coordenador") and i + 1 < len(cells) and not txts[i + 1]:
                    set_cell(cells[i + 1], d["coordenador"])
                elif tn.startswith("numero de pessoas do publico externo") and i + 1 < len(cells) and not txts[i + 1]:
                    set_cell(cells[i + 1], d["publico_externo"])
                elif tn == "/ /":
                    if dt == 0 and d["inicio"]:
                        set_cell(cells[i], d["inicio"]); dt = 1
                    elif dt == 1 and d["termino"]:
                        set_cell(cells[i], d["termino"]); dt = 2
                elif "parcial ( ) final ( )" in tn:
                    set_cell(cells[i], "Parcial ( ) Final (X)" if d["final"] else "Parcial (X) Final ( )")
                elif "(" in t and ")" in t and d["area"]:
                    for ar in AREAS:
                        if _norm(ar) == _norm(d["area"]):
                            novo = re.sub(r"\(\s*\)(\s*" + re.escape(ar) + ")", r"(1)\1", t)
                            if novo != t:
                                set_cell(cells[i], novo)
                            break
    saida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(saida))
    return d


def converter_pdf(odt: Path, out_dir: Path | None = None) -> Path | None:
    """Converte .odt -> .pdf via LibreOffice headless. Retorna o caminho ou None."""
    soffice = (shutil.which("soffice") or shutil.which("libreoffice")
               or next((p for p in ("/Applications/LibreOffice.app/Contents/MacOS/soffice",)
                        if Path(p).exists()), None))
    if not soffice:
        return None
    out_dir = Path(out_dir or odt.parent)
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir",
                    str(out_dir), str(odt)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    pdf = out_dir / (odt.stem + ".pdf")
    return pdf if pdf.exists() else None


def gerar_relatorios(consolidado_json: str | Path = "data/serra_consolidado.json",
                     out_dir: str | Path = "docs", *, apenas_pendencias: bool = True,
                     pdf: bool = False, on_progress=None) -> dict:
    """Gera <out>/relatorios-odt/<acao_id>.odt por ação (pendente, por padrão)."""
    import json
    log = on_progress or (lambda _m: None)
    cons = json.loads(Path(consolidado_json).read_text(encoding="utf-8"))
    dest = Path(out_dir) / "relatorios-odt"
    dest.mkdir(parents=True, exist_ok=True)
    feitos, pdfs = 0, 0
    for a in cons["acoes"]:
        if apenas_pendencias and (a.get("Relatório aprovado") or "").strip().lower() == "sim":
            continue
        aid = a.get("acao_id")
        if not aid:
            continue
        odt = dest / f"{aid}.odt"
        _preencher_doc(a, odt)
        feitos += 1
        if pdf and converter_pdf(odt):
            pdfs += 1
        if feitos % 20 == 0:
            log(f"  {feitos} relatórios...")
    log(f"{feitos} .odt gerados em {dest}" + (f" ({pdfs} .pdf)" if pdf else ""))
    return {"odt": feitos, "pdf": pdfs, "out": str(dest)}


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="src-etl-relatorio-odt",
                                 description="Gera o Relatório de Extensão (PROEX .odt) pré-preenchido por ação.")
    ap.add_argument("--consolidado", default="data/serra_consolidado.json")
    ap.add_argument("--out", default="docs")
    ap.add_argument("--todas", action="store_true", help="gera para todas as ações (padrão: só pendentes)")
    ap.add_argument("--pdf", action="store_true", help="também converte para PDF (precisa de LibreOffice)")
    args = ap.parse_args(argv)
    s = gerar_relatorios(args.consolidado, args.out, apenas_pendencias=not args.todas,
                         pdf=args.pdf, on_progress=print)
    print(f"OK: {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
