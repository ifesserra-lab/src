// Copia os artefatos do ETL (fora do controle do Astro) para dentro do dist,
// para servir /src/api, /src/llms.txt, /src/relatorios-odt, /src/dados-abertos.zip.
// Roda entre `astro build` e `pagefind` (pagefind ignora json/pdf).
import { cpSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

const DOCS = resolve(process.cwd(), '..', 'docs');
const DIST = resolve(process.cwd(), 'dist');

const items = [
  ['api', 'api'],
  ['relatorios-odt', 'relatorios-odt'],
  ['llms.txt', 'llms.txt'],
  ['dados-abertos.zip', 'dados-abertos.zip'],
];

let copied = 0;
for (const [src, dest] of items) {
  const from = resolve(DOCS, src);
  if (!existsSync(from)) {
    console.log(`· pula (ausente): ${src}`);
    continue;
  }
  cpSync(from, resolve(DIST, dest), { recursive: true });
  console.log(`✓ copiado: ${src}`);
  copied++;
}
console.log(`copy-assets: ${copied} item(ns) do ETL → dist/`);
