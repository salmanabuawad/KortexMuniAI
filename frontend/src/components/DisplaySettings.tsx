import { useState, type MouseEvent } from "react";
import {
  Box,
  IconButton,
  Popover,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import TuneIcon from "@mui/icons-material/Tune";
import { useTranslation } from "react-i18next";
import { useDisplay } from "../theme/display";
import type { Brightness, FontScale, ThemeName } from "../theme/index";

export function DisplaySettings() {
  const { t } = useTranslation();
  const d = useDisplay();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  return (
    <>
      <Tooltip title={t("display.title")}>
        <IconButton
          size="small"
          onClick={(e: MouseEvent<HTMLElement>) => setAnchor(e.currentTarget)}
          sx={{ color: "inherit" }}
        >
          <TuneIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Box sx={{ p: 2, minWidth: 260 }}>
          <Stack spacing={2}>
            <Row label={t("display.theme")}>
              <ToggleButtonGroup
                size="small"
                exclusive
                value={d.themeName}
                onChange={(_, v: ThemeName | null) => v && d.setThemeName(v)}
              >
                <ToggleButton value="ocean">{t("display.ocean")}</ToggleButton>
                <ToggleButton value="mist">{t("display.mist")}</ToggleButton>
              </ToggleButtonGroup>
            </Row>

            <Row label={t("display.brightness")}>
              <ToggleButtonGroup
                size="small"
                exclusive
                value={d.brightness}
                onChange={(_, v: Brightness | null) => v && d.setBrightness(v)}
              >
                <ToggleButton value="light">{t("display.light")}</ToggleButton>
                <ToggleButton value="dark">{t("display.dark")}</ToggleButton>
                <ToggleButton value="hc">{t("display.hc")}</ToggleButton>
              </ToggleButtonGroup>
            </Row>

            <Row label={t("display.fontSize")}>
              <ToggleButtonGroup
                size="small"
                exclusive
                value={d.fontScale}
                onChange={(_, v: FontScale | null) => v && d.setFontScale(v)}
              >
                <ToggleButton value="small">A-</ToggleButton>
                <ToggleButton value="base">A</ToggleButton>
                <ToggleButton value="large">A+</ToggleButton>
              </ToggleButtonGroup>
            </Row>
          </Stack>
        </Box>
      </Popover>
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
        {label}
      </Typography>
      {children}
    </Box>
  );
}
