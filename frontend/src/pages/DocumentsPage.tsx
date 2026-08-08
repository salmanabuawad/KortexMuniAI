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
import { api, uploadDocument } from "../api/client";
import type { DocumentMeta } from "../types";

function StatusChip({ doc }: { doc: DocumentMeta }) {
  const { t } = useTranslation();
  if (doc.indexing_status === "indexed")
    return <Chip size="small" color="success" variant="outlined" label={t("documents.indexed")} />;
  if (doc.indexing_status === "skipped_needs_ocr")
    return <Chip size="small" color="warning" variant="outlined" label={t("documents.needsOcr")} />;
  if (doc.processing_status === "FAILED")
    return <Chip size="small" color="error" variant="outlined" label={doc.processing_status} />;
  return <Chip size="small" variant="outlined" label={t("documents.processing")} />;
}

export function DocumentsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api<DocumentMeta[]>("/documents"),
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
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
        <Typography variant="h5">{t("documents.title")}</Typography>
        <Button
          variant="contained"
          startIcon={upload.isPending ? <CircularProgress size={16} color="inherit" /> : <UploadFileIcon />}
          disabled={upload.isPending}
          onClick={() => fileRef.current?.click()}
        >
          {upload.isPending ? t("documents.uploading") : t("documents.upload")}
        </Button>
        <input
          ref={fileRef}
          type="file"
          hidden
          onChange={onPick}
          accept=".pdf,.txt,.docx,.csv,.md,.png,.jpg,.jpeg,.webp,.tif,.tiff,.heic,.bmp,image/*"
        />
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper variant="outlined" sx={{ overflow: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("documents.name")}</TableCell>
              <TableCell>{t("documents.type")}</TableCell>
              <TableCell>{t("documents.classification")}</TableCell>
              <TableCell>{t("documents.status")}</TableCell>
              <TableCell>{t("documents.uploaded")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {docs.map((d) => (
              <TableRow key={d.id} hover>
                <TableCell>{d.title}</TableCell>
                <TableCell>{d.file_type ?? "—"}</TableCell>
                <TableCell>
                  <Chip size="small" label={d.classification} />
                </TableCell>
                <TableCell><StatusChip doc={d} /></TableCell>
                <TableCell>{new Date(d.created_at).toLocaleDateString()}</TableCell>
              </TableRow>
            ))}
            {!isLoading && docs.length === 0 && (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography color="text.secondary" sx={{ py: 3, textAlign: "center" }}>
                    {t("documents.empty")}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
