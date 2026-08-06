import nextConfig from "eslint-config-next";

const config = [
  ...nextConfig,
  {
    rules: {
      // This project hand-rolls data fetching in useEffect (fetch-on-mount, polling)
      // instead of a library like React Query/SWR. That's the standard, documented
      // "synchronizing with an external system" use of an effect — this rule flags
      // it unconditionally, including the exact hydration-safe `setMounted(true)`
      // pattern next-themes itself recommends. Not a bug; not enabling this rule.
      "react-hooks/set-state-in-effect": "off",
    },
  },
];

export default config;
