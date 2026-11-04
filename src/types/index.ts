// ===== Source =====
export interface Source {
  id: string;
  display_name: string;
  path: string;
  source_type: SourceType;
  status: SourceStatus;
  file_count: number;
  last_synced: string | null;
  created_at: string;
  updated_at: string;
  config?: SourceConfig;
}

export type SourceType =
  | "screenshots"
  | "documents"
  | "downloads"
  | "research"
  | "projects"
  | "custom";

export type SourceStatus = "active" | "paused" | "error" | "syncing";

export interface SourceConfig {
  watch_patterns?: string[];
  exclude_patterns?: string[];
  max_file_size_mb?: number;
  recursive?: boolean;
}

// ===== Document =====
export interface Document {
  id: string;
  source_id: string;
  filename: string;
  filepath: string;
  file_type: string;
  file_size: number;
  content_hash: string;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
  metadata?: Record<string, unknown>;
}

export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

// ===== Memory =====
export interface Memory {
  id: string;
  document_id: string;
  source_id: string;
  title: string;
  content: string;
  summary: string | null;
  memory_type: MemoryType;
  file_type: string;
  filepath: string;
  confidence: number;
  entities: Entity[];
  relationships: Relationship[];
  embedding_id: string | null;
  created_at: string;
  updated_at: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

export type MemoryType =
  | "text"
  | "image"
  | "code"
  | "note"
  | "conversation"
  | "web_page"
  | "screenshot";

// ===== Entity =====
export interface Entity {
  id: string;
  name: string;
  entity_type: EntityType;
  description: string | null;
  properties?: Record<string, unknown>;
  memory_count?: number;
}

export type EntityType =
  | "person"
  | "project"
  | "topic"
  | "document"
  | "event"
  | "concept"
  | "organization"
  | "location"
  | "technology";

// ===== Relationship =====
export interface Relationship {
  id: string;
  subject: Entity;
  predicate: string;
  object: Entity;
  confidence: number;
  source_memory_id: string;
}

export interface MemoryCollection {
  id: string;
  name: string;
  description?: string;
  color: string;
  icon?: string;
  item_count: number;
  is_smart: boolean;
  source_id?: string;
  created_at: string;
  updated_at: string;
  memories?: Memory[];
}

// ===== Processing Job =====
export interface ProcessingJob {
  id: string;
  document_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  current_step: string;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

// ===== Search =====
export interface SearchResult {
  memory: Memory;
  score: number;
  highlights: string[];
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
  took_ms: number;
}

// ===== Chat =====
export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: any[];
  timestamp: string;
}

export interface ChatResponse {
  answer?: string;
  message: ChatMessage;
  conversation_id?: string;
  sources: any[];
  confidence?: number;
  llm_used?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export interface ChatStorageStatus {
  engine: "postgresql" | "sqlite";
  connected: boolean;
  url?: string;
  path?: string;
  note?: string;
}

// ===== Graph =====
export interface GraphNode {
  id: string;
  label: string;
  type: EntityType;
  size: number;
  properties?: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ===== Stats =====
export interface Stats {
  total_memories: number;
  total_documents: number;
  total_entities: number;
  total_relationships: number;
  total_sources: number;
  storage_used_bytes: number;
  memories_by_type: Record<string, number>;
  memories_by_source: Record<string, number>;
  processing_queue_size: number;
  last_activity: string | null;
}

// ===== Timeline =====
export interface TimelineEntry {
  id: string;
  date: string;
  memories: Memory[];
  event_type: "created" | "updated" | "deleted" | "synced";
}

// ===== Activity =====
export interface ActivityItem {
  id: string;
  action: string;
  description: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// ===== API Response Wrapper =====
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: string;
  message?: string;
}

// ===== Pagination =====
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
