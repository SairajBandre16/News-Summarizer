import nextVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextVitals,
  {
    rules: {
      // News images come from thousands of publisher domains; next/image would
      // need a wildcard remotePattern, turning the server into an open image proxy.
      "@next/next/no-img-element": "off",
    },
  },
  { ignores: [".next/**", "node_modules/**"] },
];

export default config;
