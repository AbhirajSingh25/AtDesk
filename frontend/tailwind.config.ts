import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          forest: "#103D32",
          "forest-dark": "#0A2821",
          "forest-light": "#1A5A4A",
          ivory: "#F7F4EC",
          "ivory-dark": "#EFECE1",
          sage: "#DDE9D9",
          "sage-dark": "#C3D6BD",
          "sage-light": "#EEF5EC",
          tangerine: "#E9A16D",
          "tangerine-dark": "#D6864C",
          "tangerine-light": "#FADCC4",
          charcoal: "#282B29",
          "charcoal-muted": "#525754",
        },
      },
      fontFamily: {
        heading: ["var(--font-heading)", "Plus Jakarta Sans", "sans-serif"],
        sans: ["var(--font-sans)", "Inter", "sans-serif"],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'soft': '0 2px 10px rgba(16, 61, 50, 0.04)',
        'float': '0 8px 24px rgba(16, 61, 50, 0.08)',
        'sheet': '0 -8px 30px rgba(40, 43, 41, 0.12)',
      }
    },
  },
  plugins: [],
};
export default config;

