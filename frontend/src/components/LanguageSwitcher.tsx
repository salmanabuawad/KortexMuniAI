import { MenuItem, Select, type SelectChangeEvent } from "@mui/material";
import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "../i18n";

const LABELS: Record<string, string> = { he: "עברית", ar: "العربية", en: "English" };

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const onChange = (e: SelectChangeEvent) => {
    const lang = e.target.value;
    void i18n.changeLanguage(lang);
    localStorage.setItem("muniai.lang", lang);
  };
  return (
    <Select
      size="small"
      value={i18n.language}
      onChange={onChange}
      variant="outlined"
      sx={{ minWidth: 110, bgcolor: "background.paper" }}
    >
      {SUPPORTED_LANGUAGES.map((l) => (
        <MenuItem key={l} value={l}>
          {LABELS[l]}
        </MenuItem>
      ))}
    </Select>
  );
}
