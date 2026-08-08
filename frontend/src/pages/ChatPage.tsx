import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Box,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import AddIcon from "@mui/icons-material/Add";
import PublicIcon from "@mui/icons-material/Public";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MenuItem, Select } from "@mui/material";
import { api, streamChat, uploadDocument } from "../api/client";
import type { Agent, Conversation, DocumentMeta, Message } from "../types";
import ReactMarkdown from "react-markdown";
import { EscalationDialog } from "../components/EscalationDialog";
import { useAuth } from "../auth/AuthContext";

export function ChatPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [escalationOpen, setEscalationOpen] = useState(false);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();
  const canEscalate = user?.permissions.some((p) => p === "*" || p.startsWith("GLOBAL_AI_ESCALATION"));

  const [agentId, setAgentId] = useState<string>("");
  const [docId, setDocId] = useState<string>("");
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api<Agent[]>("/agents"),
  });
  const { data: documents = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api<DocumentMeta[]>("/documents"),
  });

  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api<Conversation[]>("/chat/conversations"),
  });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  // Pick up a question handed over from the Dashboard "Ask MuniAI" box.
  useEffect(() => {
    const pending = sessionStorage.getItem("muniai.pendingQuestion");
    if (pending) {
      setInput(pending);
      sessionStorage.removeItem("muniai.pendingQuestion");
    }
  }, []);

  const loadMessages = async (id: string) => {
    setActiveId(id);
    setMessages(await api<Message[]>(`/chat/conversations/${id}/messages`));
  };

  const newConversation = async (): Promise<string> => {
    const convo = await api<Conversation>("/chat/conversations", {
      method: "POST",
      body: JSON.stringify({}),
    });
    await qc.invalidateQueries({ queryKey: ["conversations"] });
    setActiveId(convo.id);
    setMessages([]);
    return convo.id;
  };

  const addFiles = (files: FileList | null) => {
    if (files && files.length) setAttachments((a) => [...a, ...Array.from(files)]);
  };

  const send = async () => {
    const content = input.trim();
    if ((!content && attachments.length === 0) || streaming || uploading) return;

    let id = activeId;
    if (!id) id = await newConversation();

    // Upload + index any attachments first so RAG can retrieve from them in this
    // same query (ingestion is synchronous server-side).
    if (attachments.length) {
      setUploading(true);
      try {
        for (const f of attachments) await uploadDocument(f);
        await qc.invalidateQueries({ queryKey: ["documents"] });
      } catch {
        /* surfaced below as an assistant error if the query then fails */
      }
      setUploading(false);
      setAttachments([]);
    }
    if (!content) return; // attachment-only: files are now in the knowledge base

    setInput("");

    const userMsg: Message = {
      id: `local-${Date.now()}`,
      role: "user",
      content,
      origin: "LOCAL",
      model: null,
      provider: null,
      confidence: null,
      created_at: new Date().toISOString(),
      sources: [],
    };
    setMessages((m) => [...m, userMsg]);
    setStreaming(true);
    setStreamText("");

    let acc = "";
    let failed = false;
    try {
      await streamChat(id, content, agentId || null, (event) => {
        if (event.type === "delta") {
          acc += String(event.content ?? "");
          setStreamText(acc);
        } else if (event.type === "error") {
          failed = true;
        }
      }, undefined, docId || null);
    } catch {
      failed = true;
    }

    setStreaming(false);
    setStreamText("");
    if (failed) {
      setMessages((m) => [
        ...m,
        {
          ...userMsg,
          id: `err-${Date.now()}`,
          role: "assistant",
          content: t("chat.unavailable"),
        },
      ]);
    } else {
      // Reload authoritative messages (persisted assistant message + metadata).
      setMessages(await api<Message[]>(`/chat/conversations/${id}/messages`));
      await qc.invalidateQueries({ queryKey: ["conversations"] });
    }
  };

  return (
    <Box sx={{ display: "flex", height: "100%" }}>
      {/* Conversation list */}
      <Paper
        square
        elevation={0}
        sx={{ width: 280, borderInlineEnd: 1, borderColor: "divider", display: "flex", flexDirection: "column" }}
      >
        <Box sx={{ p: 1.5 }}>
          <ListItemButton
            onClick={() => void newConversation()}
            sx={{ borderRadius: 2, border: 1, borderColor: "divider" }}
          >
            <AddIcon fontSize="small" sx={{ mr: 1 }} />
            <ListItemText primary={t("chat.newConversation")} />
          </ListItemButton>
        </Box>
        <Divider />
        <List sx={{ overflow: "auto", flexGrow: 1 }}>
          {conversations.map((c) => (
            <ListItemButton
              key={c.id}
              selected={c.id === activeId}
              onClick={() => void loadMessages(c.id)}
            >
              <ListItemText primary={c.title} primaryTypographyProps={{ noWrap: true }} />
            </ListItemButton>
          ))}
        </List>
      </Paper>

      {/* Messages + composer */}
      <Box
        sx={{ flexGrow: 1, display: "flex", flexDirection: "column", position: "relative" }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}
      >
        {dragOver && (
          <Box sx={{
            position: "absolute", inset: 0, zIndex: 5, display: "flex",
            alignItems: "center", justifyContent: "center",
            bgcolor: "action.hover", border: 2, borderStyle: "dashed",
            borderColor: "primary.main", pointerEvents: "none",
          }}>
            <Typography variant="h6" color="primary">{t("chat.dropHere")}</Typography>
          </Box>
        )}
        <Box sx={{ px: 3, pt: 2, display: "flex", justifyContent: "flex-end", gap: 1, flexWrap: "wrap" }}>
          <Select
            size="small"
            displayEmpty
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            sx={{ minWidth: 220 }}
          >
            <MenuItem value="">{t("chat.allDocuments")}</MenuItem>
            {documents.map((d) => (
              <MenuItem key={d.id} value={d.id}>{d.title}</MenuItem>
            ))}
          </Select>
          <Select
            size="small"
            displayEmpty
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            sx={{ minWidth: 220 }}
          >
            <MenuItem value="">{t("chat.generalAssistant")}</MenuItem>
            {agents.map((a) => (
              <MenuItem key={a.id} value={a.id}>
                {a.icon ? `${a.icon} ` : ""}{a.name}
              </MenuItem>
            ))}
          </Select>
        </Box>
        <Box sx={{ flexGrow: 1, overflow: "auto", p: 3 }}>
          {messages.length === 0 && !streaming && (
            <Typography color="text.secondary" sx={{ mt: 4, textAlign: "center" }}>
              {t("chat.empty")}
            </Typography>
          )}
          <Stack spacing={2} sx={{ maxWidth: 820, mx: "auto" }}>
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {streaming && (
              <Bubble role="assistant">
                {streamText || (
                  <Stack direction="row" spacing={1} alignItems="center" color="text.secondary">
                    <CircularProgress size={14} />
                    <span>{t("chat.thinking")}</span>
                  </Stack>
                )}
              </Bubble>
            )}
            <div ref={endRef} />
          </Stack>
        </Box>

        <Divider />
        <Box sx={{ p: 2 }}>
          {attachments.length > 0 && (
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap
              sx={{ maxWidth: 820, mx: "auto", mb: 1 }}>
              {attachments.map((f, i) => (
                <Chip
                  key={`${f.name}-${i}`}
                  label={f.name}
                  size="small"
                  onDelete={() => setAttachments((a) => a.filter((_, idx) => idx !== i))}
                  deleteIcon={<CloseIcon />}
                  disabled={uploading}
                />
              ))}
            </Stack>
          )}
          <Stack direction="row" spacing={1} sx={{ maxWidth: 820, mx: "auto" }} alignItems="flex-end">
            <input
              ref={fileRef}
              type="file"
              hidden
              multiple
              onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
              accept=".pdf,.txt,.docx,.csv,.md,.png,.jpg,.jpeg,.webp,.tif,.tiff,.heic,.bmp,image/*"
            />
            <IconButton
              title={t("chat.attach")}
              onClick={() => fileRef.current?.click()}
              disabled={uploading || streaming}
            >
              {uploading ? <CircularProgress size={20} /> : <AttachFileIcon />}
            </IconButton>
            <TextField
              fullWidth
              multiline
              maxRows={5}
              placeholder={t("chat.placeholder")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            {canEscalate && (
              <IconButton
                title={t("escalation.button")}
                onClick={() => setEscalationOpen(true)}
                disabled={!activeId}
              >
                <PublicIcon />
              </IconButton>
            )}
            <IconButton color="primary" onClick={() => void send()} disabled={streaming || uploading}>
              <SendIcon />
            </IconButton>
          </Stack>
        </Box>
      </Box>

      <EscalationDialog
        open={escalationOpen}
        onClose={() => setEscalationOpen(false)}
        conversationId={activeId}
        question={input || lastUserQuestion(messages)}
        onImported={async () => {
          if (activeId) setMessages(await api<Message[]>(`/chat/conversations/${activeId}/messages`));
        }}
      />
    </Box>
  );
}

function dedupeSources(sources: Message["sources"]): Message["sources"] {
  const seen = new Set<string>();
  return sources.filter((s) => {
    const key = `${s.document_id ?? ""}|${s.page ?? ""}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function lastUserQuestion(messages: Message[]): string {
  const users = messages.filter((m) => m.role === "user");
  return users.length ? users[users.length - 1].content : "";
}

function MessageBubble({ message }: { message: Message }) {
  const { t } = useTranslation();
  const isUser = message.role === "user";
  return (
    <Bubble role={message.role}>
      {isUser ? (
        <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
          {message.content}
        </Typography>
      ) : (
        <Box
          sx={{
            "& p": { m: 0, mb: 1 }, "& p:last-child": { mb: 0 },
            "& ul, & ol": { m: 0, mb: 1, pl: 3 },
            "& code": { bgcolor: "action.hover", px: 0.5, borderRadius: 0.5, fontSize: 13 },
            "& pre": { bgcolor: "action.hover", p: 1, borderRadius: 1, overflow: "auto" },
            "& table": { borderCollapse: "collapse", width: "100%" },
            "& th, & td": { border: 1, borderColor: "divider", px: 1, py: 0.5 },
          }}
        >
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </Box>
      )}
      {message.role === "assistant" && (
        <Stack spacing={1} sx={{ mt: 1 }}>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip
              size="small"
              color={
                message.origin === "EXTRACTED"
                  ? "info"
                  : message.origin === "LOCAL"
                    ? "success"
                    : "warning"
              }
              variant="outlined"
              label={
                message.origin === "EXTRACTED"
                  ? t("chat.extractedBadge")
                  : message.origin === "LOCAL"
                    ? t("chat.localBadge")
                    : t("chat.externalBadge")
              }
            />
            {message.model && <Chip size="small" variant="outlined" label={message.model} />}
          </Stack>
          {message.sources.length > 0 && (
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("chat.sources")}:
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                {dedupeSources(message.sources).map((s, i) => (
                  <Chip
                    key={`${s.document_id ?? "d"}-${s.page ?? 0}-${i}`}
                    size="small"
                    variant="outlined"
                    label={`${s.document_title ?? ""}${s.page ? ` · p.${s.page}` : ""}`}
                  />
                ))}
              </Stack>
            </Box>
          )}
        </Stack>
      )}
    </Bubble>
  );
}

function Bubble({ role, children }: { role: string; children: ReactNode }) {
  const isUser = role === "user";
  return (
    <Box sx={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
      <Paper
        elevation={0}
        sx={{
          p: 1.5,
          px: 2,
          maxWidth: "80%",
          borderRadius: 2,
          bgcolor: isUser ? "primary.main" : "background.paper",
          color: isUser ? "primary.contrastText" : "text.primary",
          border: isUser ? 0 : 1,
          borderColor: "divider",
        }}
      >
        {children}
      </Paper>
    </Box>
  );
}
