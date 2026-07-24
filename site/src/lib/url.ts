/**
 * Prefixa links internos com o base do site (import.meta.env.BASE_URL).
 * base '/'    → withBase('/painel.html') = '/painel.html'
 * base '/src/'→ withBase('/painel.html') = '/src/painel.html'
 * Use em TODO href interno para o site funcionar em GitHub Pages (/src/).
 */
const BASE = import.meta.env.BASE_URL;

export function withBase(path = '/'): string {
  const b = BASE.endsWith('/') ? BASE.slice(0, -1) : BASE;
  if (path === '/') return b + '/';
  const p = path.startsWith('/') ? path : '/' + path;
  return b + p;
}

/** Normaliza um nome como o `_norm` do Python: NFKD → ascii → minúsculas → espaços. */
export function norm(s: string): string {
  return (s || '')
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Slug de pessoa, espelho do `_slug` de dashboard/extensionistas.py.
 * Fallback quando o nome não está no índice (o índice é a fonte canônica,
 * pois resolve colisões com sufixo -2/-3 que o slug puro não conhece).
 */
export function slugify(nome: string): string {
  const s = norm(nome).replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return s || 'pessoa';
}
