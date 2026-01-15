import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Cyberpunk-inspired dark theme
        background: "#0a0e17",
        foreground: "#e8ecf4",
        primary: {
          DEFAULT: "#00d9ff",
          dark: "#0099b3",
          light: "#66e8ff",
        },
        secondary: {
          DEFAULT: "#ff3366",
          dark: "#cc1a4d",
          light: "#ff6699",
        },
        accent: {
          DEFAULT: "#9945ff",
          dark: "#7a2ed9",
          light: "#b370ff",
        },
        success: "#00ff88",
        warning: "#ffaa00",
        error: "#ff3366",
        muted: "#1a2233",
        card: "#111827",
        border: "#2a3548",
      },
      fontFamily: {
        sans: ["JetBrains Mono", "Fira Code", "monospace"],
        display: ["Orbitron", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow": "glow 2s ease-in-out infinite alternate",
        "scan": "scan 2s linear infinite",
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 5px #00d9ff, 0 0 10px #00d9ff" },
          "100%": { boxShadow: "0 0 20px #00d9ff, 0 0 30px #00d9ff" },
        },
        scan: {
          "0%": { backgroundPosition: "0% 0%" },
          "100%": { backgroundPosition: "100% 100%" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
