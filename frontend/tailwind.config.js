/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#e6f1fb", 100: "#b5d4f4",
          500: "#378add", 600: "#185fa5", 700: "#0c447c",
        },
        health: {
          50: "#e1f5ee", 100: "#9fe1cb",
          500: "#1d9e75", 600: "#0f6e56",
        },
      },
    },
  },
  plugins: [],
};
