import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { AdminStats, AuditEvent, Integration } from "../types";

interface AiSettings {
  openai_enabled: boolean;
  openai_configured: boolean;
  key_present: boolean;
  escalation_mode: string;
  openai_model: string;
  redaction_enabled: boolean;
}
interface AiUsage {
  today: { calls: number; input_tokens: number; output_tokens: number };
  month: { calls: number; input_tokens: number; output_tokens: number };
}

function AiSettingsCard() {
  const qc = useQueryClient();
  const [test, setTest] = useState<string | null>(null);
  const { data: s } = useQuery({ queryKey: ["ai-settings"], queryFn: () => api<AiSettings>("/admin/ai-settings") });
  const { data: usage } = useQuery({ queryKey: ["ai-usage"], queryFn: () => api<AiUsage>("/admin/ai-usage") });

  const setMode = useMutation({
    mutationFn: (mode: string) =>
      api("/admin/ai-settings", { method: "PUT", body: JSON.stringify({ openai_escalation_mode: mode }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-settings"] }),
  });
  const runTest = useMutation({
    mutationFn: () => api<{ configured: boolean; reachable: boolean; detail: string }>(
      "/admin/ai-settings/test", { method: "POST" }),
    onSuccess: (r) => setTest(r.reachable ? "✓ reachable" : `✗ ${r.detail}`),
    onError: () => setTest("✗ error"),
  });

  if (!s) return null;
  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
      <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>External AI (OpenAI)</Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center" sx={{ mb: 1.5 }}>
        <Chip size="small" color={s.key_present ? "success" : "default"}
          label={s.key_present ? "✓ API key configured" : "✗ No API key"} variant="outlined" />
        <Chip size="small" color={s.openai_configured ? "success" : "warning"}
          label={s.openai_configured ? "Enabled" : "Disabled"} variant="outlined" />
        <Chip size="small" variant="outlined" label={`Model: ${s.openai_model}`} />
        <Chip size="small" variant="outlined" label={s.redaction_enabled ? "Redaction on" : "Redaction off"} />
      </Stack>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="body2">Escalation:</Typography>
        <Select size="small" value={s.escalation_mode}
          onChange={(e) => setMode.mutate(e.target.value)} sx={{ minWidth: 150 }}>
          <MenuItem value="manual">Manual</MenuItem>
          <MenuItem value="automatic">Automatic</MenuItem>
          <MenuItem value="disabled">Disabled</MenuItem>
        </Select>
        <Button size="small" variant="outlined" onClick={() => runTest.mutate()} disabled={runTest.isPending}>
          Test connection
        </Button>
        {test && <Typography variant="body2" color={test.startsWith("✓") ? "success.main" : "error.main"}>{test}</Typography>}
      </Stack>
      {usage && (
        <Typography variant="body2" color="text.secondary">
          Today: {usage.today.calls} calls · {usage.today.input_tokens}/{usage.today.output_tokens} tok ·
          {" "}This month: {usage.month.calls} calls · {usage.month.input_tokens}/{usage.month.output_tokens} tok
        </Typography>
      )}
    </Paper>
  );
}

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

      <AiSettingsCard />

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
