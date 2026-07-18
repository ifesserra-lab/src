"""Consolida ações + participações num único JSON.

Casa cada ação (data/serra/acao_*.json) com o seu arquivo de participações
(data/participacoes/participacoes_<processo>.json) pelo número do processo,
embutindo as participações dentro da ação.

Saída: um único JSON com metadados + lista de ações; cada ação ganha a chave
"participacoes" (objeto com atividades/público/equipe, ou null se não coletado).

ATENÇÃO: o consolidado inclui dados pessoais (nome/CPF/e-mail dos alunos).
Mantenha local — não commitar nem publicar.

CLI:  src-etl-consolidate --acoes data/serra --part data/participacoes --out data/serra_consolidado.json
"""

from __future__ import annotations

import glob
import json
from pathlib import Path


def consolidar(
    acoes_dir: str | Path = "data/serra",
    part_dir: str | Path = "data/participacoes",
    out_json: str | Path = "data/serra_consolidado.json",
) -> Path:
    """Une ações e participações por processo num único arquivo JSON."""
    acoes = [json.loads(Path(f).read_text(encoding="utf-8"))
             for f in sorted(glob.glob(str(Path(acoes_dir) / "acao_*.json")))]

    parts: dict[str, dict] = {}
    pdir = Path(part_dir)
    if pdir.exists():
        for f in glob.glob(str(pdir / "participacoes_*.json")):
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            parts[d.get("processo")] = d

    consolidado = []
    com_part = tot_publico = tot_equipe = tot_ativ = 0
    for a in acoes:
        proc = a.get("Processo nº")
        p = parts.get(proc)
        item = dict(a)

        # participações ACHATADAS: uma entrada por pessoa (várias por ação),
        # marcando o tipo e a atividade de origem.
        participacoes: list[dict] = []
        if p:
            com_part += 1
            tot_publico += p.get("total_publico_alvo", 0)
            tot_equipe += p.get("total_equipe", 0)
            tot_ativ += p.get("total_atividades", 0)
            for ativ in p.get("atividades", []):
                ctx = {
                    "atividade_num": ativ.get("num"),
                    "atividade_id": ativ.get("atividade_id"),
                    "atividade": ativ.get("atividade"),
                }
                for pessoa in ativ.get("publico_alvo", []):
                    participacoes.append({**ctx, "tipo": "Público-alvo", **pessoa})
                for membro in ativ.get("equipe_execucao", []):
                    participacoes.append({**ctx, "tipo": "Equipe de execução", **membro})

        item["total_participacoes"] = len(participacoes)
        item["participacoes"] = participacoes  # lista (vazia se não coletado / sem participação)
        consolidado.append(item)

    campus = next((a.get("Campus") or a.get("campus") for a in acoes if a.get("Campus") or a.get("campus")), None)
    saida = {
        "campus": campus,
        "total_acoes": len(acoes),
        "acoes_com_participacoes": com_part,
        "total_atividades": tot_ativ,
        "total_publico_alvo": tot_publico,
        "total_equipe": tot_equipe,
        "acoes": consolidado,
    }
    out = Path(out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(
        prog="src-etl-consolidate",
        description="Consolida ações + participações num único JSON (local; contém PII).")
    ap.add_argument("--acoes", default="data/serra")
    ap.add_argument("--part", default="data/participacoes")
    ap.add_argument("--out", default="data/serra_consolidado.json")
    args = ap.parse_args(argv)
    p = consolidar(args.acoes, args.part, args.out)
    dados = json.loads(p.read_text(encoding="utf-8"))
    print(f"Consolidado: {p}")
    print(f"  {dados['total_acoes']} ações | {dados['acoes_com_participacoes']} com participações | "
          f"{dados['total_publico_alvo']} alunos | {dados['total_equipe']} equipe")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
