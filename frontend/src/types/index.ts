export interface Department {
  id: string;
  name: string;
  slug: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_superuser: boolean;
  locale: string;
  department: Department | null;
  permissions: string[];
}

export interface Agent {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  icon: string | null;
  enabled: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  agent_id: string | null;
  pinned: boolean;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageSource {
  document_id: string | null;
  document_title: string | null;
  page: number | null;
  snippet: string | null;
  rank: number;
}

export interface Message {
  id: string;
  role: "system" | "user" | "assistant";
  content: string;
  origin: "LOCAL" | "EXTERNAL_IMPORTED";
  model: string | null;
  provider: string | null;
  confidence: number | null;
  created_at: string;
  sources: MessageSource[];
}

export interface DocumentMeta {
  id: string;
  title: string;
  original_filename: string;
  file_type: string | null;
  classification: string;
  language: string | null;
  page_count: number | null;
  processing_status: string;
  indexing_status: string | null;
  created_at: string;
}

export interface Branding {
  org_name: string;
  accent_color: string;
  default_language: string;
  languages: string[];
}
