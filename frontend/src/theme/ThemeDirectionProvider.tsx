import { useEffect, useMemo, type ReactNode } from "react";
import { CacheProvider } from "@emotion/react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { useTranslation } from "react-i18next";
import { buildTheme, ltrCache, rtlCache } from "./index";
import { DisplayProvider, useDisplay } from "./display";
import { isRtl } from "../i18n";

function Inner({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  const { themeName, brightness, fontScale } = useDisplay();
  const rtl = isRtl(i18n.language);
  const dir = rtl ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.setAttribute("dir", dir);
    document.documentElement.setAttribute("lang", i18n.language);
  }, [dir, i18n.language]);

  const theme = useMemo(
    () => buildTheme(themeName, brightness, fontScale, dir),
    [themeName, brightness, fontScale, dir],
  );

  useEffect(() => {
    document.body.style.backgroundColor = theme.brand.appBg;
  }, [theme]);

  return (
    <CacheProvider value={rtl ? rtlCache : ltrCache}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </CacheProvider>
  );
}

// Switches theme/brightness/font (display settings) + RTL direction + emotion
// cache together so Hebrew/Arabic (RTL) and English (LTR) render correctly.
export function ThemeDirectionProvider({ children }: { children: ReactNode }) {
  return (
    <DisplayProvider>
      <Inner>{children}</Inner>
    </DisplayProvider>
  );
}
