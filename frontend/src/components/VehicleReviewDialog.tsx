import { useEffect, useMemo, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import type { ExtractionResultDTO } from "../types";

const HIGH = 0.85;
const MEDIUM = 0.5;

// Order + i18n key for each reviewable field.
const FIELD_ORDER: [string, string][] = [
  ["policy_number", "review.policyNumber"],
  ["policy_holder", "review.policyHolder"],
  ["id_number", "review.idNumber"],
  ["insurer", "review.insurer"],
  ["insurance_start", "review.insuranceStart"],
  ["insurance_end", "review.insuranceEnd"],
  ["engine_capacity", "review.engineCapacity"],
  ["production_year", "review.productionYear"],
  ["premium", "review.premium"],
  ["manufacturer", "review.manufacturer"],
  ["model", "review.model"],
  ["chassis", "review.chassis"],
];

function confColor(c: number): "success" | "warning" | "error" {
  if (c >= HIGH) return "success";
  if (c >= MEDIUM) return "warning";
  return "error";
}

interface Props {
  open: boolean;
  documentId: string | null;
  extraction: ExtractionResultDTO | null;
  onClose: () => void;
  onSaved: () => void;
}

export function VehicleReviewDialog({ open, documentId, extraction, onClose, onSaved }: Props) {
  const { t } = useTranslation();
  const veh = extraction?.fields?.vehicle_number;
  const vehConf = veh?.confidence ?? 0;

  const initial = useMemo(() => {
    const m: Record<string, string> = {};
    if (extraction) {
      for (const [k, f] of Object.entries(extraction.fields)) m[k] = f.value ?? "";
    }
    return m;
  }, [extraction]);

  const [values, setValues] = useState<Record<string, string>>({});
  const [vehicleEditing, setVehicleEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset local state whenever a new extraction arrives.
  useEffect(() => {
    setValues(initial);
    setVehicleEditing(!(veh?.value && vehConf >= MEDIUM));
  }, [initial, veh?.value, vehConf]);

  if (!extraction) return null;
  const set = (k: string, v: string) => setValues((s) => ({ ...s, [k]: v }));

  const save = async () => {
    if (!documentId) return;
    setSaving(true);
    setError(null);
    const corrections = Object.entries(values)
      .filter(([, v]) => v !== "")
      .map(([field_name, corrected_value]) => ({ field_name, corrected_value }));
    try {
      await api(`/vehicles/documents/${documentId}/verify`, {
        method: "POST",
        body: JSON.stringify(corrections),
      });
      onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const showMaybe = veh?.value && vehConf >= MEDIUM && vehConf < HIGH && !vehicleEditing;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t("review.title")}</DialogTitle>
      <DialogContent dividers>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {/* Document type */}
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">{t("review.documentType")}:</Typography>
          <Chip size="small" label={extraction.document_type}
            color={confColor(extraction.document_type_confidence)} />
        </Stack>

        {/* Vehicle number — the headline field */}
        <Box sx={{ mb: 2, p: 2, borderRadius: 2, border: 1, borderColor: "divider" }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>{t("review.vehicleNumber")}</Typography>

          {veh?.value && vehConf >= HIGH && !vehicleEditing ? (
            <Stack direction="row" spacing={1} alignItems="center">
              <CheckCircleIcon color="success" fontSize="small" />
              <Typography variant="h6">{values.vehicle_number ?? veh.value}</Typography>
              <Chip size="small" color="success" label={`${Math.round(vehConf * 100)}%`} />
              <Button size="small" onClick={() => setVehicleEditing(true)}>{t("review.change")}</Button>
            </Stack>
          ) : showMaybe ? (
            <Stack spacing={1}>
              <Typography>{t("review.maybeVehicle")} <b>{veh?.value}</b></Typography>
              <Stack direction="row" spacing={1}>
                <Button size="small" variant="contained"
                  onClick={() => { set("vehicle_number", veh!.value!); setVehicleEditing(false); }}>
                  {t("review.confirm")}
                </Button>
                <Button size="small" onClick={() => setVehicleEditing(true)}>{t("review.change")}</Button>
              </Stack>
            </Stack>
          ) : (
            <>
              {!veh?.value && <Alert severity="warning" sx={{ mb: 1 }}>{t("review.noVehicle")}</Alert>}
              <TextField
                fullWidth size="small" autoFocus
                value={values.vehicle_number ?? ""}
                onChange={(e) => set("vehicle_number", e.target.value)}
                placeholder="7046676"
              />
            </>
          )}
        </Box>

        {/* Other fields */}
        <Stack spacing={1.5}>
          {FIELD_ORDER.filter(([k]) => extraction.fields[k]).map(([k, labelKey]) => {
            const f = extraction.fields[k];
            return (
              <TextField
                key={k}
                label={t(labelKey)}
                size="small"
                fullWidth
                value={values[k] ?? ""}
                onChange={(e) => set(k, e.target.value)}
                error={f.confidence < MEDIUM}
                helperText={f.confidence < MEDIUM ? t("review.lowConfidence") : undefined}
                InputProps={{
                  endAdornment: (
                    <Chip size="small" variant="outlined" color={confColor(f.confidence)}
                      label={`${Math.round(f.confidence * 100)}%`} />
                  ),
                }}
              />
            );
          })}
        </Stack>

        {/* Debug view */}
        <Accordion sx={{ mt: 2, boxShadow: "none", border: 1, borderColor: "divider" }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="body2">{t("review.debug")}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="caption" color="text.secondary">
              {t("review.engine")}: {extraction.ocr_engine}
            </Typography>
            <Divider sx={{ my: 1 }} />
            <Typography variant="caption" color="text.secondary">{t("review.anchors")}:</Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ my: 0.5 }}>
              {extraction.anchors_detected.map((a, i) => (
                <Chip key={i} size="small" variant="outlined" label={a} />
              ))}
            </Stack>
            <Typography variant="caption" color="text.secondary">{t("review.candidates")}:</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>{t("review.score")}</TableCell>
                  <TableCell>{t("review.anchors")}</TableCell>
                  <TableCell>{t("review.selected")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {extraction.vehicle_candidates.map((c, i) => (
                  <TableRow key={i} sx={{ bgcolor: c.selected ? "action.selected" : undefined }}>
                    <TableCell>{c.value}</TableCell>
                    <TableCell>{c.score}</TableCell>
                    <TableCell>{c.label ?? c.reason}</TableCell>
                    <TableCell>{c.selected ? "✓" : ""}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </AccordionDetails>
        </Accordion>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("review.cancel")}</Button>
        <Button variant="contained" onClick={save} disabled={saving}>{t("review.save")}</Button>
      </DialogActions>
    </Dialog>
  );
}
