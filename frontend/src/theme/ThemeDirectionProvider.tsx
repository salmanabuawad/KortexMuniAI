import { useEffect, useMemo, type ReactNode } from "react";
import { CacheProvider } from "@emotion/react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { useTranslation } from "react-i18next";
import { buildTheme, ltrCache, rtlCache } from "./index";
import { isRtl } from "../i18n";

// Switches MUI direction + emotion cache + <html dir/lang> whenever the language
// changes, so RTL (Hebrew/Arabic) and LTR (English) layouts render correctly.
export function ThemeDirectionProvider({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  const rtl = isRtl(i18n.language);
  const dir = rtl ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.setAttribute("dir", dir);
    document.documentElement.setAttribute("lang", i18n.language);
  }, [dir, i18n.language]);

  const theme = useMemo(() => buildTheme(dir), [dir]);

  return (
    <CacheProvider value={rtl ? rtlCache : ltrCache}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </CacheProvider>
  );
}
