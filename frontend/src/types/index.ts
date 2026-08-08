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

export interface Vehicle {
  id: string;
  registration_number: string;
  normalized_number: string;
  manufacturer: string | null;
  model: string | null;
  is_active: boolean;
}

export interface InsuranceConflict {
  id: string;
  vehicle_id: string | null;
  conflict_type: string;
  overlap_days: number | null;
  severity: string;
  status: string;
  notes: string | null;
}

export interface ExtractionField {
  value: string | null;
  confidence: number;
  source: string;
  page: number;
  label_detected: string | null;
  reason: string | null;
}

export interface VehicleCandidate {
  value: string;
  score: number;
  label: string | null;
  reason: string;
  selected: boolean;
}

export interface ExtractionResultDTO {
  document_type: string;
  document_type_confidence: number;
  fields: Record<string, ExtractionField>;
  vehicle_candidates: VehicleCandidate[];
  anchors_detected: string[];
  warnings: string[];
  ocr_engine: string;
  processing_version: string;
}

export interface VehicleUploadResult {
  document: { id: string; document_type: string; original_filename: string };
  extraction: ExtractionResultDTO;
}

export interface Integration {
  id: string;
  name: string;
  kind: string;
  enabled: boolean;
  status: string;
}

export interface AuditEvent {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  result: string;
  detail: string | null;
  created_at: string;
}

export interface AdminStats {
  users: number;
  documents: number;
  conversations: number;
  vehicles: number;
  conflicts: number;
}

export interface EscalationPrepared {
  escalation_id: string;
  prompt: string;
  detected_types: string[];
  sensitivity: string;
}

export interface Branding {
  org_name: string;
  accent_color: string;
  default_language: string;
  languages: string[];
}
