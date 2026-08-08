import { useState, type FormEvent } from "react";
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import SendIcon from "@mui/icons-material/AutoAwesome";
import DocumentsIcon from "@mui/icons-material/Description";
import ChatIcon from "@mui/icons-material/ChatBubbleOutline";
import VehiclesIcon from "@mui/icons-material/DirectionsCar";
import WarningIcon from "@mui/icons-material/ReportGmailerrorred";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Conversation, DocumentMeta, InsuranceConflict, Vehicle } from "../types";

interface Health {
  status: string;
  components: { name: string; healthy: boolean }[];
}

export function DashboardPage() {
  const { t } = useTranslation();
  const theme = useTheme();
  const b = theme.brand;
  const navigate = useNavigate();
  const { user } = useAuth();
  const [q, setQ] = useState("");

  const { data: health } = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/health") });
  const { data: docs = [] } = useQuery({ queryKey: ["documents"], queryFn: () => api<DocumentMeta[]>("/documents") });
  const { data: convos = [] } = useQuery({ queryKey: ["conversations"], queryFn: () => api<Conversation[]>("/chat/conversations") });
  const { data: vehicles = [] } = useQuery({ queryKey: ["vehicles"], queryFn: () => api<Vehicle[]>("/vehicles") });
  const { data: conflicts = [] } = useQuery({ queryKey: ["conflicts"], queryFn: () => api<InsuranceConflict[]>("/vehicles/conflicts") });

  const ai = health?.components.find((c) => c.name.startsWith("ai"));
  const db = health?.components.find((c) => c.name === "database");

  const ask = (e: FormEvent) => {
    e.preventDefault();
    if (q.trim()) sessionStorage.setItem("muniai.pendingQuestion", q.trim());
    navigate("/chat");
  };

  const stats = [
    { icon: <DocumentsIcon />, label: t("dashboard.documents"), value: docs.length, to: "/documents" },
    { icon: <ChatIcon />, label: t("dashboard.conversations"), value: convos.length, to: "/chat" },
    { icon: <VehiclesIcon />, label: t("dashboard.vehicles"), value: vehicles.length, to: "/vehicles" },
    { icon: <WarningIcon />, label: t("dashboard.conflicts"), value: conflicts.length, to: "/vehicles",
      warn: conflicts.length > 0 },
  ];

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1200, mx: "auto" }}>
      {/* Hero / Ask MuniAI */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 3, md: 4 },
          mb: 3,
          borderRadius: 3,
          color: "#fff",
          background: `linear-gradient(135deg, ${b.headerBg}, ${b.accentActive})`,
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 800 }}>
          {t("dashboard.welcome")}
        </Typography>
        <Typography sx={{ opacity: 0.85, mb: 2 }}>
          {user?.full_name}
        </Typography>
        <form onSubmit={ask}>
          <TextField
            fullWidth
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("dashboard.askPlaceholder")}
            sx={{
              bgcolor: "rgba(255,255,255,0.95)",
              borderRadius: 2,
              "& fieldset": { border: "none" },
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SendIcon color="primary" />
                </InputAdornment>
              ),
            }}
          />
        </form>
      </Paper>

      {/* Stat cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {stats.map((s) => (
          <Grid item xs={6} md={3} key={s.label}>
            <Card>
              <CardActionArea onClick={() => navigate(s.to)}>
                <CardContent>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Box sx={{ color: s.warn ? b.destructive : b.accent }}>{s.icon}</Box>
                    <Box>
                      <Typography variant="h5" sx={{ fontWeight: 800, color: s.warn ? b.destructive : undefined }}>
                        {s.value}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">{s.label}</Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* System status */}
        <Grid item xs={12} md={5}>
          <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
            {t("dashboard.systemStatus")}
          </Typography>
          <Card>
            <CardContent>
              <Stack spacing={1.5}>
                <StatusRow label={t("dashboard.aiService")} ok={!!ai?.healthy}
                  okText={t("dashboard.healthy")} downText={t("dashboard.down")} />
                <StatusRow label={t("dashboard.database")} ok={!!db?.healthy}
                  okText={t("dashboard.healthy")} downText={t("dashboard.down")} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent conversations */}
        <Grid item xs={12} md={7}>
          <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 700 }}>
            {t("dashboard.recentConversations")}
          </Typography>
          <Card>
            <CardContent sx={{ p: 0 }}>
              {convos.slice(0, 6).map((c) => (
                <CardActionArea key={c.id} onClick={() => navigate("/chat")}
                  sx={{ px: 2, py: 1.25, borderBottom: `1px solid ${b.cardBorder}` }}>
                  <Typography noWrap>{c.title}</Typography>
                </CardActionArea>
              ))}
              {convos.length === 0 && (
                <Typography color="text.secondary" sx={{ p: 2 }}>{t("dashboard.none")}</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

function StatusRow({ label, ok, okText, downText }: { label: string; ok: boolean; okText: string; downText: string }) {
  return (
    <Stack direction="row" alignItems="center" justifyContent="space-between">
      <Typography>{label}</Typography>
      <Chip size="small" color={ok ? "success" : "error"} variant="outlined" label={ok ? okText : downText} />
    </Stack>
  );
}
