/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#faf8f5",
        surface: "#ffffff",
        "surface-hover": "#f3efe6",
        "surface-active": "#ebe5d8",
        border: "#e7e2d6",
        "border-hover": "#d5cebf",
        primary: "#1c1917",
        "primary-hover": "#292524",
        "primary-muted": "#f0ebe1",
        secondary: "#57534e",
        accent: "#78716c",
        success: "#16a34a",
        warning: "#ca8a04",
        danger: "#dc2626",
        "text-primary": "#1c1917",
        "text-secondary": "#57534e",
        "text-tertiary": "#8c827a",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-in": "slideIn 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
