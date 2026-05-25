import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0f4c81",
          dark: "#062a4d",
        },
        risk: "#dc2626",
        caution: "#d97706",
        normal: "#16a34a",
      },
    },
  },
  plugins: [],
};

export default config;
