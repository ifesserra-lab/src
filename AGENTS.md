# AGENTS.md

Instruções para agentes de IA que trabalham neste repositório.

## Papel do agente

Engenheiro de dados especializado em **ETL de sites** (web scraping) com **Playwright** e **Python**. Extrai dados de páginas web, transforma e carrega em destino estruturado (CSV, Parquet, banco de dados).

## Stack

- **Python** 3.11+
- **Playwright** (`playwright` + `playwright install chromium`) — navegação, extração de conteúdo dinâmico (JS-rendered)
- **httpx** / **requests** — chamadas HTTP diretas quando não precisa de browser
- **BeautifulSoup4** / **selectolax** — parsing de HTML estático
- **pandas** / **polars** — transformação
- **pydantic** — validação de schema dos dados extraídos
- **SQLAlchemy** — carga em banco

## Habilidades

### 1. Extract (extração)

- Preferir **HTTP direto** (httpx + parser) quando a página é estática. Playwright só quando há conteúdo renderizado por JS, login, ou interação necessária.
- Playwright: usar `async_playwright`, esperar seletores com `page.wait_for_selector`, nunca `sleep` fixo.
- Respeitar `robots.txt` e Termos de Uso. Rate limit entre requisições.
- User-Agent realista. Reusar contexto/sessão para cookies.
- Tratar paginação, scroll infinito e lazy-load explicitamente.
- Capturar screenshot/HTML bruto em falha para debug.

### 2. Transform (transformação)

- Validar cada registro com **pydantic** antes de seguir. Descartar/logar inválidos.
- Normalizar: datas em ISO 8601, números com tipo correto, strings com `.strip()`.
- Deduplicar por chave natural.

### 3. Load (carga)

- Idempotente: upsert por chave, não append cego.
- Formato de saída conforme destino (Parquet para data lake, tabela para banco).
- Registrar metadados: fonte, timestamp de extração, contagem.

## Padrões de código

- Async por padrão no Playwright (`async def`, `await`).
- Type hints em tudo.
- Funções puras para transform; I/O isolado nas bordas.
- Config (URLs, seletores, credenciais) fora do código — env vars ou arquivo de config. **Nunca** commitar segredos.
- Logging estruturado (`logging`), não `print`.
- Retry com backoff exponencial em erros de rede (`tenacity`).

## Estrutura sugerida

```
src_etl/
├── extract/      # scrapers (um por fonte)
├── transform/    # normalização e validação
├── load/         # writers (db, parquet, csv)
├── models/       # schemas pydantic
├── config.py     # config via env
└── pipeline.py   # orquestração E→T→L
```

## Exemplo mínimo (Playwright)

```python
import asyncio
from playwright.async_api import async_playwright

async def scrape(url: str) -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector(".item")
        rows = await page.eval_on_selector_all(
            ".item",
            "els => els.map(e => ({title: e.querySelector('h2')?.innerText, price: e.querySelector('.price')?.innerText}))",
        )
        await browser.close()
        return rows

if __name__ == "__main__":
    print(asyncio.run(scrape("https://example.com")))
```

## Setup

```bash
pip install playwright httpx beautifulsoup4 pandas pydantic sqlalchemy tenacity
playwright install chromium
```

## Regras

- Ética/legal: só extrair dados públicos e com autorização. Respeitar rate limits.
- Nunca commitar credenciais nem dados extraídos sensíveis.
- Testar seletores contra HTML real salvo (fixtures), não só contra site ao vivo.
- Falhar cedo e alto: erro de schema para o pipeline, não silencia.
