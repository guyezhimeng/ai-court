/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        court: {
          bg: '#07090f',
          panel: '#0f1219',
          panel2: '#141824',
          line: '#1c2236',
          text: '#dde4f8',
          muted: '#5a6b92',
          ok: '#2ecc8a',
          warn: '#f5c842',
          danger: '#ff5270',
          acc: '#6a9eff',
          acc2: '#a07aff',
        },
      },
      fontFamily: {
        serif: ['Noto Serif SC', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
