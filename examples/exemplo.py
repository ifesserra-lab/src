"""Exemplos de uso da lib `src_etl`.

Rode:  python examples/exemplo.py
(Requer:  pip install -e .  &&  playwright install chromium)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src_etl import Acao, extrair_campi, listar_campi, run


def log(msg: str) -> None:
    print(f"  · {msg}")


# ---------------------------------------------------------------------------
# 1) Listar os campi disponíveis
# ---------------------------------------------------------------------------
def exemplo_listar_campi() -> None:
    print("\n[1] Campi disponíveis:")
    campi = asyncio.run(listar_campi())
    print("   ", ", ".join(campi))


# ---------------------------------------------------------------------------
# 2) Um campus (com limite, para ser rápido) -> salva JSON por ação
# ---------------------------------------------------------------------------
def exemplo_um_campus() -> None:
    print("\n[2] Extraindo 3 ações do campus Serra -> ./saida")
    dados = run("Serra", out_dir="saida", max_acoes=3, on_progress=log)
    acoes = dados["Serra"]
    print(f"    {len(acoes)} ações salvas em saida/serra/")

    # lê de volta um JSON salvo
    arq = next(Path("saida/serra").glob("acao_*.json"))
    registro = json.loads(arq.read_text(encoding="utf-8"))
    print(f"    Exemplo ({arq.name}): {registro['Título ação']}")


# ---------------------------------------------------------------------------
# 3) Um conjunto de campi
# ---------------------------------------------------------------------------
def exemplo_conjunto() -> None:
    print("\n[3] Extraindo um conjunto de campi (2 ações cada)")
    dados = run(["Serra", "Vitória"], out_dir="saida", max_acoes=2, on_progress=log)
    for campus, acoes in dados.items():
        print(f"    {campus}: {len(acoes)} ações")


# ---------------------------------------------------------------------------
# 4) Todos os campi (comentado — demorado: baixa tudo)
# ---------------------------------------------------------------------------
def exemplo_todos() -> None:
    print("\n[4] Todos os campi (pode demorar bastante)")
    dados = run(None, out_dir="saida", on_progress=log)   # None = todos
    total = sum(len(v) for v in dados.values())
    print(f"    {total} ações em {len(dados)} campi")


# ---------------------------------------------------------------------------
# 5) API async direta (sem salvar) — trabalha com objetos Acao
# ---------------------------------------------------------------------------
def exemplo_async() -> None:
    print("\n[5] API async — objetos Acao em memória")

    async def _run() -> list[Acao]:
        dados = await extrair_campi("Serra", max_acoes=2, on_progress=log)
        return dados["Serra"]

    acoes = asyncio.run(_run())
    for a in acoes:
        print(f"    {a.acao_id} | {a.tipo} | {a.coordenador} | {a.titulo}")


if __name__ == "__main__":
    exemplo_listar_campi()
    exemplo_um_campus()
    exemplo_async()
    # exemplo_conjunto()   # descomente para testar conjunto
    # exemplo_todos()      # descomente para baixar TODOS (demorado)
