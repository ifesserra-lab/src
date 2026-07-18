"""CLI da etapa autenticada (participações: público-alvo + equipe).

Exemplos:
    # processos explícitos
    src-etl-part --processo 23158.002622/2025-41 --out data/participacoes

    # a partir do índice gerado pela etapa pública
    src-etl-part --from-index data/serra/_index.json --out data/participacoes

Credenciais: .env (USER / PASSWORD) ou variáveis de ambiente.
"""

from __future__ import annotations

import argparse
import sys

from .pipeline import processos_de_index, run_participacoes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="src-etl-part",
        description="Coleta público-alvo (alunos atendidos) e equipe executora por processo.",
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--processo", nargs="+", metavar="PROC",
                     help="Um ou mais números de processo")
    grp.add_argument("--from-index", metavar="PATH",
                     help="Lê os processos de um _index.json da etapa pública")

    parser.add_argument("--out", default="data/participacoes", help="Diretório de saída")
    parser.add_argument("--workers", type=int, default=1,
                        help="Abas paralelas numa única sessão (um login). Ex.: 3")
    parser.add_argument("--no-headless", action="store_true", help="Mostra o navegador")
    args = parser.parse_args(argv)

    processos = (processos_de_index(args.from_index)
                 if args.from_index else args.processo)
    if not processos:
        print("Nenhum processo para coletar.", file=sys.stderr)
        return 1

    dados = run_participacoes(
        processos,
        out_dir=args.out,
        headless=not args.no_headless,
        workers=args.workers,
        on_progress=lambda m: print(f"[src-etl-part] {m}", file=sys.stderr),
    )
    tot_pa = sum(a.total_publico_alvo for a in dados.values())
    tot_eq = sum(a.total_equipe for a in dados.values())
    print(f"{len(dados)} processos | público-alvo={tot_pa} equipe={tot_eq} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
