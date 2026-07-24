/// <reference types="vitest" />
import { getViteConfig } from 'astro/config';

// getViteConfig faz o vitest entender .astro (Container API).
export default getViteConfig({
  test: {
    include: ['tests/**/*.test.ts'],
  },
});
