import { Box, Chip, Paper, Stack, Typography } from "@mui/material";
import ConstructionIcon from "@mui/icons-material/Construction";
import { useTranslation } from "react-i18next";

// Honest placeholder for roadmap modules (spec §74: mark future integrations as
// "Coming Later" rather than pretending they work).
export function ComingLaterPage({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  return (
    <Box sx={{ p: 4, display: "flex", justifyContent: "center" }}>
      <Paper elevation={0} sx={{ p: 5, maxWidth: 560, border: 1, borderColor: "divider", borderRadius: 3 }}>
        <Stack spacing={2} alignItems="center" textAlign="center">
          <ConstructionIcon color="disabled" sx={{ fontSize: 48 }} />
          <Typography variant="h5">{t(titleKey)}</Typography>
          <Chip label={t("common.comingLater")} variant="outlined" />
          <Typography color="text.secondary">{t("comingLater.body")}</Typography>
        </Stack>
      </Paper>
    </Box>
  );
}
