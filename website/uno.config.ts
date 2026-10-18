import { defineConfig, presetUno, presetAttributify, presetIcons } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
    presetIcons({
      scale: 1.2,
      warn: true,
    }),
  ],
  shortcuts: {
    'glass-panel': 'bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-2xl shadow-2xl shadow-purple-950/20',
    'glass-card': 'bg-slate-900/40 backdrop-blur-md border border-slate-800/60 rounded-xl hover:border-purple-500/30 transition-all duration-300',
    'gradient-text': 'bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent font-extrabold',
    'btn-glow': 'relative group overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 px-6 py-3 font-semibold text-white shadow-lg transition-all duration-300 hover:shadow-purple-500/30 hover:scale-[1.02] active:scale-[0.98]',
    'btn-outline': 'px-6 py-3 rounded-xl border border-slate-700 bg-slate-900/80 hover:bg-slate-800/80 text-slate-200 font-semibold transition-all duration-200 hover:border-slate-600 flex items-center justify-center gap-2 cursor-pointer',
    'terminal-header': 'bg-slate-950/80 border-b border-slate-800/80 px-4 py-3 flex items-center justify-between rounded-t-2xl',
  },
  theme: {
    colors: {
      brand: {
        50: '#f0f5ff',
        500: '#6366f1',
        600: '#4f46e5',
        900: '#1e1b4b',
      },
    },
  },
})
