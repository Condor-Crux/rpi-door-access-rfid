/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      fontFamily: {
        nunito: ['Nunito', 'ui-rounded', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
