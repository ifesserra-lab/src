# SRC_ETL

Lib Python para **ETL das ações públicas do SRC/Ifes** (Sistema de Registro e
Emissão de Certificados). Navega a consulta pública com **Playwright**, baixa o
detalhe de cada ação com **httpx** e salva **um JSON por ação**.

## Instalação

O pacote é publicado como **wheel/sdist anexado a cada GitHub Release**
(GitHub Packages não hospeda pacotes Python).

```bash
# direto do repositório (branch main)
pip install "git+https://github.com/ifesserra-lab/SRC_ETL.git"

# a partir de um release específico (wheel anexado)
pip install "https://github.com/ifesserra-lab/SRC_ETL/releases/download/v0.1.0/src_etl-0.1.0-py3-none-any.whl"

playwright install chromium
```

## Uso — CLI

```bash
# um campus
src-etl --campus Serra --out data

# um conjunto de campi
src-etl --campus Serra Vitória --out data

# todos os campi
src-etl --all --out data

# só listar os campi disponíveis
src-etl --list-campi

# teste rápido (limita nº de ações por campus)
src-etl --campus Serra --max 5 --out data
```

Saída: `data/<campus>/acao_<id>.json` + `data/<campus>/_index.json`.

## Uso — API

```python
from src_etl import run, extrair_campi, listar_campi, Acao

# síncrono: extrai e salva
dados = run("Serra", out_dir="data", max_acoes=5)   # {campus: [Acao, ...]}

# conjunto ou todos
run(["Serra", "Vitória"], out_dir="data")
run(None, out_dir="data")           # None = todos os campi
```

O parâmetro **campus** aceita: `None` (todos), `"Serra"` (um) ou
`["Serra", "Vitória"]` (conjunto). O **diretório de saída** é o parâmetro
`out_dir` (CLI: `--out`).

## Como funciona (ETL)

1. **Extract** — Playwright abre a consulta pública, seleciona o campus, clica
   em *Pesquisar* e percorre todas as páginas; em cada linha abre o dialog
   *Detalhes* para capturar o `id` da ação.
2. **Transform** — a página de detalhe (render server-side) é baixada por httpx
   e o `panelGrid` (pares rótulo/valor) é convertido num modelo `Acao`
   (validado com pydantic).
3. **Load** — grava um JSON por ação em `out_dir/<campus>/`.

## Desenvolvimento

```bash
pip install -e ".[dev]"
playwright install chromium
pytest
```

## Licença

MIT.
