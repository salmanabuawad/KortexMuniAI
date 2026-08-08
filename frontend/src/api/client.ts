// Thin fetch wrapper. Same-origin in production (Nginx); proxied /api in dev.

const TOKEN_KEY = "muniai.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

const BASE = "/api/v1";

interface ApiError {
  error?: { message?: string; code?: string };
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const resp = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    let message = `Request failed (${resp.status})`;
    try {
      const body = (await resp.json()) as ApiError;
      message = body.error?.message ?? message;
    } catch {
      /* non-JSON error body */
    }
    if (resp.status === 401) clearToken();
    throw new Error(message);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export async function uploadDocument(
  file: File,
  classification = "INTERNAL",
): Promise<unknown> {
  const form = new FormData();
  form.append("file", file);
  form.append("classification", classification);
  const token = getToken();
  const resp = await fetch(`${BASE}/documents`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form, // no Content-Type: browser sets the multipart boundary
  });
  if (!resp.ok) {
    let message = `Upload failed (${resp.status})`;
    try {
      const body = (await resp.json()) as { error?: { message?: string } };
      message = body.error?.message ?? message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  return resp.json();
}

/**
 * Open an SSE stream for chat. Uses fetch (not EventSource) so we can send the
 * Authorization header and a POST body. Calls onEvent for each parsed data line.
 */
export async function streamChat(
  conversationId: string,
  content: string,
  agentId: string | null,
  onEvent: (event: Record<string, unknown>) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken();
  const resp = await fetch(`${BASE}/chat/conversations/${conversationId}/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ content, agent_id: agentId }),
    signal,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`Stream failed (${resp.status})`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      try {
        onEvent(JSON.parse(line.slice(5).trim()));
      } catch {
        /* ignore malformed chunk */
      }
    }
  }
}
