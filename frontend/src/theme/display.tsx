import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Brightness, FontScale, ThemeName } from "./index";

interface DisplayState {
  themeName: ThemeName;
  brightness: Brightness;
  fontScale: FontScale;
  setThemeName: (t: ThemeName) => void;
  setBrightness: (b: Brightness) => void;
  setFontScale: (f: FontScale) => void;
}

const KEY = "muniai.display";

function load(): Pick<DisplayState, "themeName" | "brightness" | "fontScale"> {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { themeName: "ocean", brightness: "light", fontScale: "base", ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  return { themeName: "ocean", brightness: "light", fontScale: "base" };
}

const DisplayCtx = createContext<DisplayState | undefined>(undefined);

export function DisplayProvider({ children }: { children: ReactNode }) {
  const initial = load();
  const [themeName, setThemeNameS] = useState<ThemeName>(initial.themeName);
  const [brightness, setBrightnessS] = useState<Brightness>(initial.brightness);
  const [fontScale, setFontScaleS] = useState<FontScale>(initial.fontScale);

  const persist = useCallback(
    (next: Partial<Pick<DisplayState, "themeName" | "brightness" | "fontScale">>) => {
      const merged = { themeName, brightness, fontScale, ...next };
      localStorage.setItem(KEY, JSON.stringify(merged));
    },
    [themeName, brightness, fontScale],
  );

  const value = useMemo<DisplayState>(
    () => ({
      themeName,
      brightness,
      fontScale,
      setThemeName: (t) => { setThemeNameS(t); persist({ themeName: t }); },
      setBrightness: (b) => { setBrightnessS(b); persist({ brightness: b }); },
      setFontScale: (f) => { setFontScaleS(f); persist({ fontScale: f }); },
    }),
    [themeName, brightness, fontScale, persist],
  );

  return <DisplayCtx.Provider value={value}>{children}</DisplayCtx.Provider>;
}

export function useDisplay(): DisplayState {
  const ctx = useContext(DisplayCtx);
  if (!ctx) throw new Error("useDisplay must be used within DisplayProvider");
  return ctx;
}
