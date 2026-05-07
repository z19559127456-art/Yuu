import * as path from 'path'
import { defineProject } from 'vitest/config'
import viteConfig from './vite.config'

export default defineProject(({ mode }) => {
  return {
    ...viteConfig,
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      css: true,
    },
  }
})
