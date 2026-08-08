import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { en } from "./en";
import { he } from "./he";
import { ar } from "./ar";

export const SUPPORTED_LANGUAGES = ["he", "ar", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];
export const RTL_LANGUAGES: Language[] = ["he", "ar"];

export function isRtl(lang: string): boolean {
  return RTL_LANGUAGES.includes(lang as Language);
}

const stored = (localStorage.getItem("muniai.lang") as Language) || "he";

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    he: { translation: he },
    ar: { translation: ar },
  },
  lng: stored,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
