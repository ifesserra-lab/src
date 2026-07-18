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

# crawl público em paralelo (K abas dividem as páginas — agiliza; ignora --max)
src-etl --campus Serra --workers 4 --out data
```

> **Paralelismo:** só a etapa pública paraleliza (`--workers`), pois não tem
> login. A etapa autenticada (participações) **não** paraleliza: o SRC mantém
> uma única sessão por usuário e a paginação das tabelas é via AJAX (precisa de
> navegador) — logins concorrentes colidem. Ela salva 1 JSON por processo
> incrementalmente e faz *resume* (pula processos já salvos numa nova execução).

Saída: `data/<campus>/acao_<id>.json` + `data/<campus>/_index.json`.

### Participações (autenticado) — alunos atendidos + equipe executora

Após baixar as ações, esta etapa entra em **Gerenciar → Ações**, pesquisa pelo
**número do processo** e, para cada atividade, coleta o **público-alvo (alunos
atendidos)** e a **equipe de execução**, gerando **um JSON por processo**.

Exige login. Coloque as credenciais no `.env` (já ignorado pelo git):

```
USER=seu_usuario
PASSWORD=sua_senha
```

```bash
# processos explícitos
src-etl-part --processo 23158.002622/2025-41 --out data/participacoes

# reaproveitando o índice da etapa pública (todos os processos daquele campus)
src-etl-part --from-index data/serra/_index.json --out data/participacoes
```

Saída: `data/participacoes/participacoes_<processo>.json`, no formato:

```json
{
  "processo": "23158.002622/2025-41",
  "total_atividades": 10,
  "total_publico_alvo": 79,
  "total_equipe": 25,
  "atividades": [
    {
      "num": "002", "atividade": "...", "atividade_id": "22066",
      "publico_alvo": [ {"Nome": "...", "CPF": "...", "E-mail": "...", "Situação": "..."} ],
      "equipe_execucao": [ {"Nome": "...", "Função": "...", "Vínculo": "..."} ]
    }
  ]
}
```

> ⚠️ **Dados pessoais**: esta etapa coleta nome, CPF e e-mail de alunos.
> O resultado fica **apenas local** (`data/` está no `.gitignore`) — nunca
> commite nem publique. Use somente com acesso autorizado ao sistema.

## Uso — API

```python
from src_etl import run, extrair_campi, listar_campi, Acao

# síncrono: extrai e salva
dados = run("Serra", out_dir="data", max_acoes=5)   # {campus: [Acao, ...]}

# conjunto ou todos
run(["Serra", "Vitória"], out_dir="data")
run(None, out_dir="data")           # None = todos os campi

# etapa autenticada: participações por processo (1 JSON por processo)
from src_etl import run_participacoes, processos_de_index
run_participacoes(["23158.002622/2025-41"], out_dir="data/participacoes")
run_participacoes(processos_de_index("data/serra/_index.json"), out_dir="data/participacoes")
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
