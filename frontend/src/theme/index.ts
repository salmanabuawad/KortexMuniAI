import { createTheme, type Theme } from "@mui/material/styles";
import createCache from "@emotion/cache";
import rtlPlugin from "stylis-plugin-rtl";
import { prefixer } from "stylis";

// Fluent-inspired, calm municipal enterprise look (spec §49).
export function buildTheme(dir: "rtl" | "ltr", accent = "#0F6CBD"): Theme {
  return createTheme({
    direction: dir,
    palette: {
      mode: "light",
      primary: { main: accent },
      background: { default: "#F5F7FA", paper: "#FFFFFF" },
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: [
        "Segoe UI",
        "Assistant",
        "Rubik",
        "system-ui",
        "Arial",
        "sans-serif",
      ].join(","),
    },
    components: {
      MuiButton: { defaultProps: { disableElevation: true } },
    },
  });
}

export const ltrCache = createCache({ key: "mui", stylisPlugins: [prefixer] });
export const rtlCache = createCache({
  key: "muirtl",
  stylisPlugins: [prefixer, rtlPlugin],
});
