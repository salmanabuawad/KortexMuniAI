import { MenuItem, Select, type SelectChangeEvent } from "@mui/material";
import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "../i18n";

const LABELS: Record<string, string> = { he: "עברית", ar: "العربية", en: "English" };

export function LanguageSwitcher({ inHeader = false }: { inHeader?: boolean }) {
  const { i18n } = useTranslation();
  const onChange = (e: SelectChangeEvent) => {
    const lang = e.target.value;
    void i18n.changeLanguage(lang);
    localStorage.setItem("muniai.lang", lang);
  };

  if (inHeader) {
    return (
      <Select
        size="small"
        value={i18n.language}
        onChange={onChange}
        variant="standard"
        disableUnderline
        sx={{
          color: "inherit",
          fontSize: 14,
          "& .MuiSelect-icon": { color: "inherit" },
          "&:before, &:after": { display: "none" },
        }}
      >
        {SUPPORTED_LANGUAGES.map((l) => (
          <MenuItem key={l} value={l}>{LABELS[l]}</MenuItem>
        ))}
      </Select>
    );
  }

  return (
    <Select
      size="small"
      value={i18n.language}
      onChange={onChange}
      variant="outlined"
      sx={{ minWidth: 110, bgcolor: "background.paper" }}
    >
      {SUPPORTED_LANGUAGES.map((l) => (
        <MenuItem key={l} value={l}>{LABELS[l]}</MenuItem>
      ))}
    </Select>
  );
}
