"""Vínculos autoritativos entre ações (programa guarda-chuva -> ações filhas).

O campo texto "Ação vinculante" do detalhe é incompleto. A fonte correta é
`consulta-acao-vinculada.xhtml?acao_vinculante=<acao_id>`, que lista as ações
vinculadas a uma ação-mãe. Este módulo busca esses vínculos por acao_id e
grava "acoes_vinculadas" (lista de filhas, por processo) em cada acao_*.json.

CLI:  src-etl-vinculadas --acoes data/serra
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .detail import BASE, USER_AGENT

VINC_URL = BASE + "consulta-acao-vinculada.xhtml?acao_vinculante="


def fetch_vinculadas(acao_id: str, client: httpx.Client) -> list[dict[str, str]]:
    """Devolve as ações vinculadas (filhas) de uma ação-mãe, pela fonte oficial."""
    r = client.get(f"{VINC_URL}{acao_id}", timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    filhas = []
    for tr in soup.select("table tbody tr"):
        c = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if len(c) >= 4 and c[0] and "nenhum" not in c[0].lower():
            filhas.append({"processo": c[0], "natureza": c[1], "tipo": c[2], "titulo": c[3]})
    return filhas


def enriquecer_vinculadas(acoes_dir: str | Path = "data/serra", *, on_progress=None) -> dict:
    """Grava 'acoes_vinculadas' em cada acao_*.json a partir da fonte oficial."""
    log = on_progress or (lambda _m: None)
    arquivos = sorted(glob.glob(str(Path(acoes_dir) / "acao_*.json")))
    stats = {"acoes": 0, "com_filhas": 0, "total_filhas": 0, "erros": 0}
    with httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT}) as cli:
        for f in arquivos:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            aid = d.get("acao_id")
            if not aid:
                continue
            stats["acoes"] += 1
            try:
                filhas = fetch_vinculadas(aid, cli)
            except Exception as e:
                stats["erros"] += 1
                log(f"  ! erro acao_id={aid}: {str(e)[:60]}")
                continue
            d["acoes_vinculadas"] = filhas
            Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            if filhas:
                stats["com_filhas"] += 1
                stats["total_filhas"] += len(filhas)
                log(f"  {d.get('Processo nº')} -> {len(filhas)} vinculadas")
    log(f"stats: {stats}")
    return stats


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="src-etl-vinculadas",
                                 description="Grava vínculos autoritativos (ações filhas) por ação.")
    ap.add_argument("--acoes", default="data/serra")
    args = ap.parse_args(argv)
    s = enriquecer_vinculadas(args.acoes, on_progress=lambda m: print(f"[vinc] {m}", file=sys.stderr))
    print(f"vínculos: {s['com_filhas']} ações-mãe | {s['total_filhas']} filhas | erros {s['erros']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
