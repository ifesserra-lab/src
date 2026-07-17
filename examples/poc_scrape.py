"""POC ETL — entra no site do SRC/Ifes e extrai dados básicos.

Extract: abre a página com Playwright, pega título + links.
Transform: normaliza os links (remove vazios, resolve URL absoluta).
Load: salva em data/output.json e tira screenshot.

Uso:
    pip install playwright
    playwright install chromium
    python poc_scrape.py
"""

import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

URL = "https://src.ifes.edu.br"
OUT_DIR = Path(__file__).parent / "data"


async def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Extract -----------------------------------------------------
        await page.goto(URL, wait_until="networkidle")
        final_url = page.url
        title = await page.title()

        raw_links = await page.eval_on_selector_all(
            "a",
            "els => els.map(e => ({text: e.innerText.trim(), href: e.getAttribute('href')}))",
        )

        # screenshot pra prova/debug
        await page.screenshot(path=str(OUT_DIR / "page.png"), full_page=True)
        await browser.close()

    # Transform -------------------------------------------------------
    links = [
        {"text": l["text"], "href": urljoin(final_url, l["href"])}
        for l in raw_links
        if l["href"]
    ]

    result = {
        "url_final": final_url,
        "titulo": title,
        "total_links": len(links),
        "links": links,
    }

    # Load ------------------------------------------------------------
    out_file = OUT_DIR / "output.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Título: {title}")
    print(f"URL final: {final_url}")
    print(f"Links extraídos: {len(links)}")
    print(f"Salvo em: {out_file}")
    print(f"Screenshot: {OUT_DIR / 'page.png'}")


if __name__ == "__main__":
    asyncio.run(main())
