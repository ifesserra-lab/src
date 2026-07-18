"""CLI da lib.

Exemplos:
    src-etl --campus Serra --out data           # um campus
    src-etl --campus Serra Vitória --out data   # conjunto
    src-etl --all --out data                    # todos os campi
"""

from __future__ import annotations

import argparse
import sys

from .etl.pipeline import run
from .etl.scraper import listar_campi
import asyncio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="src-etl",
        description="ETL das ações públicas do SRC/Ifes (por campus).",
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--campus", nargs="+", metavar="CAMPUS",
                     help="Um ou mais campi (ex.: --campus Serra Vitória)")
    grp.add_argument("--all", action="store_true", help="Todos os campi")
    grp.add_argument("--list-campi", action="store_true", help="Lista os campi e sai")

    parser.add_argument("--out", default="data", help="Diretório-base de saída")
    parser.add_argument("--max", type=int, default=None, help="Limite de ações por campus (teste)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Abas paralelas no crawl público (agiliza; ignora --max)")
    parser.add_argument("--no-headless", action="store_true", help="Mostra o navegador")
    args = parser.parse_args(argv)

    headless = not args.no_headless

    if args.list_campi:
        for c in asyncio.run(listar_campi(headless=headless)):
            print(c)
        return 0

    campus = None if args.all else args.campus
    dados = run(
        campus,
        out_dir=args.out,
        headless=headless,
        max_acoes=args.max,
        workers=args.workers,
        on_progress=lambda m: print(f"[src-etl] {m}", file=sys.stderr),
    )
    total = sum(len(v) for v in dados.values())
    print(f"{total} ações em {len(dados)} campus(es) salvas em {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
