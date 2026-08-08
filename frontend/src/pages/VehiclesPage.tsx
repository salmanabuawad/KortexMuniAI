import { useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, uploadVehicleDocument } from "../api/client";
import type { InsuranceConflict, Vehicle, VehicleUploadResult } from "../types";
import { VehicleReviewDialog } from "../components/VehicleReviewDialog";

const SEVERITY_COLOR: Record<string, "default" | "warning" | "error" | "info"> = {
  INFO: "info",
  WARNING: "warning",
  HIGH: "error",
  CRITICAL: "error",
};

export function VehiclesPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<VehicleUploadResult | null>(null);

  const { data: vehicles = [] } = useQuery({
    queryKey: ["vehicles"],
    queryFn: () => api<Vehicle[]>("/vehicles"),
  });
  const { data: conflicts = [] } = useQuery({
    queryKey: ["conflicts"],
    queryFn: () => api<InsuranceConflict[]>("/vehicles/conflicts"),
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadVehicleDocument(file) as Promise<VehicleUploadResult>,
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["vehicles"] });
      qc.invalidateQueries({ queryKey: ["conflicts"] });
      setReview(result); // open the review screen with detected fields
    },
    onError: (e: Error) => setError(e.message),
  });

  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setError(null);
      upload.mutate(file);
    }
    e.target.value = "";
  };

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h5">{t("vehicles.title")}</Typography>
        <Button
          variant="contained"
          startIcon={upload.isPending ? <CircularProgress size={16} color="inherit" /> : <UploadFileIcon />}
          disabled={upload.isPending}
          onClick={() => fileRef.current?.click()}
        >
          {t("vehicles.upload")}
        </Button>
        <input ref={fileRef} type="file" hidden onChange={onPick}
          accept=".pdf,.txt,.png,.jpg,.jpeg,.webp,.tif,.tiff,.heic,.bmp,image/*" />
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Typography variant="subtitle1" sx={{ mb: 1 }}>{t("vehicles.conflicts")}</Typography>
      <Paper variant="outlined" sx={{ mb: 3, overflow: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("vehicles.type")}</TableCell>
              <TableCell>{t("vehicles.severity")}</TableCell>
              <TableCell>{t("vehicles.overlapDays")}</TableCell>
              <TableCell>{t("vehicles.notes")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {conflicts.map((c) => (
              <TableRow key={c.id} hover>
                <TableCell>{c.conflict_type}</TableCell>
                <TableCell>
                  <Chip size="small" color={SEVERITY_COLOR[c.severity] ?? "default"} label={c.severity} />
                </TableCell>
                <TableCell>{c.overlap_days ?? "—"}</TableCell>
                <TableCell>{c.notes}</TableCell>
              </TableRow>
            ))}
            {conflicts.length === 0 && (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography color="text.secondary" sx={{ py: 2, textAlign: "center" }}>
                    {t("vehicles.noConflicts")}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      <Paper variant="outlined" sx={{ overflow: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("vehicles.plate")}</TableCell>
              <TableCell>{t("admin.status")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {vehicles.map((v) => (
              <TableRow key={v.id} hover>
                <TableCell>{v.registration_number}</TableCell>
                <TableCell>
                  <Chip size="small" color={v.is_active ? "success" : "default"}
                    label={v.is_active ? "active" : "inactive"} variant="outlined" />
                </TableCell>
              </TableRow>
            ))}
            {vehicles.length === 0 && (
              <TableRow>
                <TableCell colSpan={2}>
                  <Typography color="text.secondary" sx={{ py: 2, textAlign: "center" }}>
                    {t("vehicles.none")}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      <VehicleReviewDialog
        open={review !== null}
        documentId={review?.document.id ?? null}
        extraction={review?.extraction ?? null}
        onClose={() => setReview(null)}
        onSaved={() => {
          qc.invalidateQueries({ queryKey: ["vehicles"] });
          qc.invalidateQueries({ queryKey: ["conflicts"] });
        }}
      />
    </Box>
  );
}
