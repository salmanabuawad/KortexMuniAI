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
import { useTranslation } from "react-i18next";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, streamChat } from "../api/client";
import type { Conversation, Message } from "../types";

export function ChatPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api<Conversation[]>("/chat/conversations"),
  });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

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

  const send = async () => {
    const content = input.trim();
    if (!content || streaming) return;
    setInput("");

    let id = activeId;
    if (!id) id = await newConversation();

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
      await streamChat(id, content, null, (event) => {
        if (event.type === "delta") {
          acc += String(event.content ?? "");
          setStreamText(acc);
        } else if (event.type === "error") {
          failed = true;
        }
      });
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
    <Box sx={{ display: "flex", height: "calc(100vh - 64px)" }}>
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
      <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
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
          <Stack direction="row" spacing={1} sx={{ maxWidth: 820, mx: "auto" }}>
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
            <IconButton color="primary" onClick={() => void send()} disabled={streaming}>
              <SendIcon />
            </IconButton>
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const { t } = useTranslation();
  return (
    <Bubble role={message.role}>
      <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
        {message.content}
      </Typography>
      {message.role === "assistant" && (
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          <Chip
            size="small"
            color={message.origin === "LOCAL" ? "success" : "warning"}
            variant="outlined"
            label={message.origin === "LOCAL" ? t("chat.localBadge") : t("chat.externalBadge")}
          />
          {message.model && <Chip size="small" variant="outlined" label={message.model} />}
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
