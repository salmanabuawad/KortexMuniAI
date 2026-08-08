import { createTheme, type Theme } from "@mui/material/styles";
import createCache from "@emotion/cache";
import rtlPlugin from "stylis-plugin-rtl";
import { prefixer } from "stylis";

// ---------------------------------------------------------------------------
// Kortex Digital shared design system (reference: buildingsmanager).
// Ported as TOKENS so every Kortex app shares one look. Two themes (ocean/mist),
// three brightness levels (light/dark/high-contrast), three font scales.
// ---------------------------------------------------------------------------

export type ThemeName = "ocean" | "mist";
export type Brightness = "light" | "dark" | "hc";
export type FontScale = "small" | "base" | "large";

export interface BrandTokens {
  headerBg: string;
  headerText: string;
  railBg: string;
  railHover: string;
  railActive: string;
  railIndicator: string;
  railText: string;
  accent: string;
  accentHover: string;
  accentActive: string;
  favorite: string;
  destructive: string;
  appBg: string;
  panel: string;
  paper: string;
  cardBorder: string;
  inputBorder: string;
  textPrimary: string;
  textMuted: string;
}

// Module augmentation so components can read `theme.brand.*`.
declare module "@mui/material/styles" {
  interface Theme {
    brand: BrandTokens;
  }
  interface ThemeOptions {
    brand?: BrandTokens;
  }
}

const FONT_STACK =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Assistant", "Rubik", sans-serif';

const FONT_BASE: Record<FontScale, number> = { small: 15, base: 16, large: 18 };

// Base ocean tokens (light).
const OCEAN_LIGHT: BrandTokens = {
  headerBg: "#2E62A2",
  headerText: "#FFFFFF",
  railBg: "#2F4D52",
  railHover: "#3D6971",
  railActive: "#3D6971",
  railIndicator: "#66CCFF",
  railText: "#CFE0E3",
  accent: "#2196F3",
  accentHover: "#1976D2",
  accentActive: "#1565C0",
  favorite: "#6BBF56",
  destructive: "#F44336",
  appBg: "#F7F9FA",
  panel: "#F0F0F0",
  paper: "#FFFFFF",
  cardBorder: "#E5E7EB",
  inputBorder: "#CED4DA",
  textPrimary: "#333333",
  textMuted: "#6C757D",
};

// Mist = cooler slate variant of the same system.
const MIST_LIGHT: BrandTokens = {
  ...OCEAN_LIGHT,
  headerBg: "#3E5C76",
  railBg: "#2A3B47",
  railHover: "#3A5060",
  railActive: "#3A5060",
  railIndicator: "#7FD1E8",
  accent: "#4C86C6",
  accentHover: "#3A6EA5",
  accentActive: "#2E5A8A",
  appBg: "#F4F6F8",
  panel: "#ECEFF3",
};

function applyDark(t: BrandTokens): BrandTokens {
  return {
    ...t,
    headerBg: "#1E3350",
    railBg: "#141C24",
    railHover: "#22303C",
    railActive: "#22303C",
    railText: "#AEBEC8",
    appBg: "#0F1720",
    panel: "#16202B",
    paper: "#1B2732",
    cardBorder: "#2A3742",
    inputBorder: "#3A4753",
    textPrimary: "#E6EDF3",
    textMuted: "#9AA7B4",
  };
}

function applyHighContrast(t: BrandTokens): BrandTokens {
  return {
    ...t,
    headerBg: "#000000",
    headerText: "#FFFFFF",
    railBg: "#000000",
    railHover: "#1A1A1A",
    railActive: "#1A1A1A",
    railIndicator: "#66CCFF",
    railText: "#FFFFFF",
    accent: "#66CCFF",
    accentHover: "#33BBFF",
    accentActive: "#00AAFF",
    appBg: "#000000",
    panel: "#0A0A0A",
    paper: "#000000",
    cardBorder: "#FFFFFF",
    inputBorder: "#FFFFFF",
    textPrimary: "#FFFFFF",
    textMuted: "#D0D0D0",
  };
}

export function resolveTokens(themeName: ThemeName, brightness: Brightness): BrandTokens {
  const base = themeName === "mist" ? MIST_LIGHT : OCEAN_LIGHT;
  if (brightness === "dark") return applyDark(base);
  if (brightness === "hc") return applyHighContrast(base);
  return base;
}

export function buildTheme(
  themeName: ThemeName,
  brightness: Brightness,
  fontScale: FontScale,
  dir: "rtl" | "ltr",
): Theme {
  const b = resolveTokens(themeName, brightness);
  const mode = brightness === "light" ? "light" : "dark";

  return createTheme({
    direction: dir,
    brand: b,
    palette: {
      mode,
      primary: { main: b.accent, dark: b.accentActive, light: b.accentHover },
      success: { main: b.favorite },
      error: { main: b.destructive },
      background: { default: b.appBg, paper: b.paper },
      text: { primary: b.textPrimary, secondary: b.textMuted },
      divider: b.cardBorder,
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: FONT_STACK,
      fontSize: FONT_BASE[fontScale],
      h4: { fontWeight: 700 },
      h5: { fontWeight: 700 },
      h6: { fontWeight: 700 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    components: {
      MuiButton: { defaultProps: { disableElevation: true } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
      MuiCard: {
        styleOverrides: {
          root: { border: `1px solid ${b.cardBorder}`, boxShadow: "none" },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          notchedOutline: { borderColor: b.inputBorder },
        },
      },
      MuiTooltip: { defaultProps: { arrow: true } },
    },
  });
}

export const ltrCache = createCache({ key: "mui", stylisPlugins: [prefixer] });
export const rtlCache = createCache({
  key: "muirtl",
  stylisPlugins: [prefixer, rtlPlugin],
});
