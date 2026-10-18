import { defineConfig } from 'vite'
import type { Plugin, ViteDevServer } from 'vite'
import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// Publish installers and a pip source archive from the actual CLI checkout.
function installerEndpoint(): Plugin {
  const root = path.resolve(import.meta.dirname, '..')
  const version = readFileSync(path.join(root, 'version.txt'), 'utf8').trim()
  const packageName = `packages/amagi_cli-${version}.tar.gz`
  const readAsset = (name: string): { source: string | Buffer; contentType: string } | undefined => {
    if (name === 'install' || name === 'install.ps1') {
      return {
        source: readFileSync(path.join(root, name === 'install' ? 'install.sh' : 'install.ps1'), 'utf8'),
        contentType: 'text/plain; charset=utf-8',
      }
    }
    if (name === packageName) {
      return {
        source: execFileSync(process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'), [path.resolve(import.meta.dirname, 'scripts/package-cli.py')]),
        contentType: 'application/gzip',
      }
    }
  }
  const serveInstaller = (server: Pick<ViteDevServer, 'middlewares'>) => {
    server.middlewares.use((request, response, next) => {
      const name = request.url?.split('?')[0].slice(1)
      if (!name || !['install', 'install.ps1', packageName].includes(name) || !['GET', 'HEAD'].includes(request.method || '')) return next()
      try {
        const asset = readAsset(name)!
        response.setHeader('Content-Type', asset.contentType)
        response.setHeader('X-Content-Type-Options', 'nosniff')
        response.end(request.method === 'HEAD' ? undefined : asset.source)
      } catch (error) { next(error) }
    })
  }
  return {
    name: 'amagi-installer',
    configureServer: serveInstaller,
    configurePreviewServer: serveInstaller,
    generateBundle() {
      for (const fileName of ['install', 'install.ps1', packageName]) {
        this.emitFile({ type: 'asset', fileName, source: readAsset(fileName)!.source })
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    installerEndpoint(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
})
