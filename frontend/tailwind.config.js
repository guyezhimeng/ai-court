/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        court: {
          bg: '#0d0d1a',
          panel: '#1a1a2e',
          panel2: '#16213e',
          sidebar: '#0f0f23',
          line: 'rgba(212,165,116,0.15)',
          text: '#e5e5e5',
          muted: '#a3a3a3',
          dim: '#666666',
          ok: '#22c55e',
          warn: '#eab308',
          danger: '#ef4444',
          info: '#3b82f6',
          acc: '#d4a574',
          acc2: '#c49464',
        },
      },
      fontFamily: {
        serif: ['Noto Serif SC', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
