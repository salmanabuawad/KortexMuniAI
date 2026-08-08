import { useState, type FormEvent } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { LanguageSwitcher } from "../components/LanguageSwitcher";

export function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
    } catch {
      setError(t("login.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        p: 2,
      }}
    >
      <Card sx={{ width: 420, maxWidth: "100%", borderRadius: 3 }} elevation={3}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={3}>
            <Stack direction="row" alignItems="center" justifyContent="space-between">
              <Stack direction="row" spacing={1.5} alignItems="center">
                <LockOutlinedIcon color="primary" />
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {t("app.name")}
                </Typography>
              </Stack>
              <LanguageSwitcher />
            </Stack>

            <Typography variant="h6">{t("login.title")}</Typography>

            {error && <Alert severity="error">{error}</Alert>}

            <form onSubmit={onSubmit}>
              <Stack spacing={2}>
                <TextField
                  label={t("login.email")}
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                  required
                  fullWidth
                />
                <TextField
                  label={t("login.password")}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  fullWidth
                />
                <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
                  {t("login.submit")}
                </Button>
              </Stack>
            </form>

            <Alert severity="info" icon={false} sx={{ fontSize: 13 }}>
              {t("login.localNotice")}
            </Alert>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
