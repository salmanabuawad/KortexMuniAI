import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import type { EscalationPrepared } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  conversationId: string | null;
  question: string;
  onImported: () => void;
}

const SEV_COLOR: Record<string, "success" | "warning" | "error"> = {
  low: "success",
  medium: "warning",
  high: "error",
};

export function EscalationDialog({ open, onClose, conversationId, question, onImported }: Props) {
  const { t } = useTranslation();
  const [prepared, setPrepared] = useState<EscalationPrepared | null>(null);
  const [promptText, setPromptText] = useState("");
  const [answer, setAnswer] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setAnswer("");
    setCopied(false);
    api<EscalationPrepared>("/escalation/prepare", {
      method: "POST",
      body: JSON.stringify({ question, conversation_id: conversationId }),
    })
      .then((p) => {
        setPrepared(p);
        setPromptText(p.prompt);
      })
      .catch((e: Error) => setError(e.message));
  }, [open, question, conversationId]);

  const copy = async () => {
    await navigator.clipboard.writeText(promptText);
    setCopied(true);
  };

  const importAnswer = async () => {
    if (!conversationId || !answer.trim()) return;
    try {
      await api("/escalation/import", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId, answer }),
      });
      onImported();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{t("escalation.title")}</DialogTitle>
      <DialogContent dividers>
        <Alert severity="info" sx={{ mb: 2 }}>{t("escalation.intro")}</Alert>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {prepared && (
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="body2">{t("escalation.sensitivity")}:</Typography>
            <Chip size="small" color={SEV_COLOR[prepared.sensitivity] ?? "default"}
              label={prepared.sensitivity} />
            {prepared.detected_types.length > 0 && (
              <>
                <Typography variant="body2">· {t("escalation.detected")}:</Typography>
                {prepared.detected_types.map((d) => (
                  <Chip key={d} size="small" variant="outlined" label={d} />
                ))}
              </>
            )}
          </Stack>
        )}

        <TextField
          label="Prompt"
          multiline
          minRows={8}
          fullWidth
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
        />
        <Box sx={{ mt: 1 }}>
          <Button startIcon={<ContentCopyIcon />} onClick={copy} variant="outlined" size="small">
            {copied ? t("escalation.copied") : t("escalation.copy")}
          </Button>
        </Box>

        <TextField
          label={t("escalation.pasteLabel")}
          multiline
          minRows={4}
          fullWidth
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          sx={{ mt: 3 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("escalation.cancel")}</Button>
        <Button onClick={importAnswer} variant="contained" disabled={!answer.trim()}>
          {t("escalation.import")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
