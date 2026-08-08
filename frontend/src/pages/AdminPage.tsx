import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { AdminStats, AuditEvent, Integration } from "../types";

interface ModelsInfo {
  provider: string;
  healthy: boolean;
  detail: string;
  models: string[];
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h4">{value}</Typography>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
      </CardContent>
    </Card>
  );
}

export function AdminPage() {
  const { t } = useTranslation();
  const { data: stats } = useQuery({ queryKey: ["admin-stats"], queryFn: () => api<AdminStats>("/admin/stats") });
  const { data: integrations = [] } = useQuery({
    queryKey: ["admin-integrations"], queryFn: () => api<Integration[]>("/admin/integrations"),
  });
  const { data: audit = [] } = useQuery({
    queryKey: ["admin-audit"], queryFn: () => api<AuditEvent[]>("/admin/audit?limit=50"),
  });
  const { data: models } = useQuery({
    queryKey: ["admin-models"], queryFn: () => api<ModelsInfo>("/admin/models"),
  });

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>{t("admin.title")}</Typography>

      {stats && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={2.4}><Stat label={t("admin.users")} value={stats.users} /></Grid>
          <Grid item xs={6} md={2.4}><Stat label={t("admin.documents")} value={stats.documents} /></Grid>
          <Grid item xs={6} md={2.4}><Stat label={t("admin.conversations")} value={stats.conversations} /></Grid>
          <Grid item xs={6} md={2.4}><Stat label={t("admin.vehicles")} value={stats.vehicles} /></Grid>
          <Grid item xs={6} md={2.4}><Stat label={t("admin.conflicts")} value={stats.conflicts} /></Grid>
        </Grid>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>{t("admin.models")}</Typography>
          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <Chip size="small" label={models?.provider ?? "—"} />
              <Chip size="small" color={models?.healthy ? "success" : "error"}
                label={models?.healthy ? "healthy" : "down"} variant="outlined" />
            </Stack>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {(models?.models ?? []).map((m) => <Chip key={m} size="small" variant="outlined" label={m} />)}
            </Stack>
          </Paper>

          <Typography variant="subtitle1" sx={{ mb: 1 }}>{t("admin.integrations")}</Typography>
          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableBody>
                {integrations.map((i) => (
                  <TableRow key={i.id}>
                    <TableCell>{i.name}</TableCell>
                    <TableCell align="right">
                      <Chip size="small" variant="outlined"
                        color={i.enabled ? "success" : "default"}
                        label={i.enabled ? "enabled" : t("admin.comingLater")} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>{t("admin.audit")}</Typography>
          <Paper variant="outlined" sx={{ overflow: "auto", maxHeight: 480 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>{t("admin.action")}</TableCell>
                  <TableCell>{t("admin.status")}</TableCell>
                  <TableCell>{t("admin.when")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {audit.map((a) => (
                  <TableRow key={a.id} hover>
                    <TableCell>{a.action}</TableCell>
                    <TableCell>
                      <Chip size="small" variant="outlined"
                        color={a.result === "success" ? "success" : "error"} label={a.result} />
                    </TableCell>
                    <TableCell>{new Date(a.created_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
