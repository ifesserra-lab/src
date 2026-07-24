// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// F5 vai apontar `outDir` para ../docs e ligar base '/src' (GitHub Pages).
// Na PoC (F1) mantemos base '/' e saída em dist/ para diff visual local.
export default defineConfig({
  site: 'https://ifesserra-lab.github.io',
  base: '/src', // GitHub Pages do repo ifesserra-lab/src → servido em /src/
  integrations: [sitemap()],
  // 'preserve' espelha a estrutura do site atual (misto):
  //   painel.astro          → painel.html
  //   acoes/[id].astro      → acoes/108.html
  //   acoes/index.astro     → acoes/index.html  (servido em /acoes/)
  // Zero 404 em links indexados/externos.
  build: { format: 'preserve' },
});
