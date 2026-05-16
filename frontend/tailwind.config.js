/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'aura': {
          'bg': '#0a0e1a',
          'card': '#111827',
          'border': '#1f2937',
          'accent': '#6366f1',
          'green': '#10b981',
          'red': '#ef4444',
          'gold': '#f59e0b',
          'blue': '#3b82f6',
        }
      }
    },
  },
  plugins: [],
}
