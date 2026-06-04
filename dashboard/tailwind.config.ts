import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#1E40AF",
        "on-primary": "#FFFFFF",
        secondary: "#3B82F6",
        accent: "#D97706",
        background: "#F8FAFC",
        foreground: "#1E3A8A",
        muted: "#E9EEF6",
        "muted-fg": "#64748B",
        border: "#DBEAFE",
        destructive: "#DC2626",
        success: "#15803D",
      },
      fontFamily: {
        sans: ["var(--font-fira-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-fira-code)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
