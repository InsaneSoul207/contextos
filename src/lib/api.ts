import type {
  Source,
  Memory,
  Document,
  Entity,
  SearchResponse,
  ChatResponse,
  Conversation,
  ConversationDetail,
  ChatStorageStatus,
  MemoryCollection,
  GraphData,
  Stats,
  TimelineEntry,
  ActivityItem,
  ApiResponse,
  PaginatedResponse,
} from "@/types";

const BASE_URL = "http://127.0.0.1:44480";

class ApiClient {
  private baseUrl: string;
  private apiKey: string | null = null;

  constructor(baseUrl: string = BASE_URL) {
    this.baseUrl = baseUrl;
  }

  setApiKey(key: string) {
    this.apiKey = key;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorBody = await response.text();
        throw new ApiError(
          response.status,
          `API Error ${response.status}: ${errorBody}`
        );
      }

      if (response.status === 204) {
        return undefined as T;
      }

      const text = await response.text();
      return (text ? JSON.parse(text) : undefined) as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(0, `Network error: ${(error as Error).message}`);
    }
  }

  private async requestUpload<T>(
    endpoint: string,
    formData: FormData
  ): Promise<T> {
    const headers: Record<string, string> = {};
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new ApiError(
        response.status,
        `API Error ${response.status}: ${errorBody}`
      );
    }

    return (await response.json()) as T;
  }

  // ===== Sources =====
  async listSources(): Promise<Source[]> {
    return this.request<Source[]>("/api/sources");
  }

  async getSource(id: string): Promise<Source> {
    return this.request<Source>(`/api/sources/${id}`);
  }

  async createSource(data: {
    display_name: string;
    path: string;
    source_path?: string;
    source_type?: string;
    config?: Record<string, unknown>;
  }): Promise<Source> {
    const payload = {
      display_name: data.display_name,
      source_path: data.source_path || data.path,
      path: data.path || data.source_path,
      source_type: data.source_type || "folder",
      config: data.config,
    };
    return this.request<Source>("/api/sources", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async updateSource(
    id: string,
    data: Partial<Source>
  ): Promise<Source> {
    return this.request<Source>(`/api/sources/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteSource(id: string): Promise<void> {
    await this.request<void>(`/api/sources/${id}`, {
      method: "DELETE",
    });
  }

  async syncSource(id: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/sources/${id}/sync`, {
      method: "POST",
    });
  }

  // ===== Documents =====
  async listDocuments(params?: {
    source_id?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<Document>> {
    const query = new URLSearchParams();
    if (params?.source_id) query.set("source_id", params.source_id);
    if (params?.status) query.set("status", params.status);
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    const qs = query.toString();
    return this.request<PaginatedResponse<Document>>(
      `/api/documents${qs ? `?${qs}` : ""}`
    );
  }

  async getDocument(id: string): Promise<Document> {
    return this.request<Document>(`/api/documents/${id}`);
  }

  async deleteDocument(id: string): Promise<void> {
    await this.request<void>(`/api/documents/${id}`, {
      method: "DELETE",
    });
  }

  async uploadDocument(
    file: File,
    sourceId?: string
  ): Promise<Document> {
    const formData = new FormData();
    formData.append("file", file);
    if (sourceId) {
      formData.append("source_id", sourceId);
    }
    return this.requestUpload<Document>("/api/documents/upload", formData);
  }

  // ===== Memories =====
  async listMemories(params?: {
    source_id?: string;
    memory_type?: string;
    type?: string;
    file_type?: string;
    search?: string;
    page?: number;
    per_page?: number;
    sort?: string;
  }): Promise<PaginatedResponse<Memory>> {
    const query = new URLSearchParams();
    if (params?.source_id) query.set("source_id", params.source_id);
    const mType = params?.memory_type || params?.type;
    if (mType) query.set("memory_type", mType);
    if (params?.file_type) query.set("file_type", params.file_type);
    if (params?.search) query.set("search", params.search);
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.sort) query.set("sort", params.sort);
    const qs = query.toString();
    return this.request<PaginatedResponse<Memory>>(
      `/api/memories${qs ? `?${qs}` : ""}`
    );
  }

  async getMemory(id: string): Promise<Memory> {
    return this.request<Memory>(`/api/memories/${id}`);
  }

  async deleteMemory(id: string): Promise<void> {
    await this.request<void>(`/api/memories/${id}`, {
      method: "DELETE",
    });
  }

  async getRelatedMemories(id: string, limit?: number): Promise<Memory[]> {
    const query = limit ? `?limit=${limit}` : "";
    return this.request<Memory[]>(`/api/memories/${id}/related${query}`);
  }

  // ===== Search & Chat =====
  async search(
    query: string,
    options?: {
      limit?: number;
      file_type?: string;
      source_id?: string;
    }
  ): Promise<SearchResponse> {
    return this.request<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, ...options }),
    });
  }

  async chat(
    message: string,
    conversationId?: string,
    history?: Array<{ role: string; content: string }>
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        history,
      }),
    });
  }

  // ===== Conversations (Multi-Session & PostgreSQL Persistence) =====
  async listConversations(limit: number = 50): Promise<Conversation[]> {
    return this.request<Conversation[]>(`/api/conversations?limit=${limit}`);
  }

  async createConversation(title?: string): Promise<Conversation> {
    return this.request<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ title: title || "New Chat" }),
    });
  }

  async getConversation(id: string): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/api/conversations/${id}`);
  }

  async deleteConversation(id: string): Promise<void> {
    await this.request<void>(`/api/conversations/${id}`, {
      method: "DELETE",
    });
  }

  async getChatStorageStatus(): Promise<ChatStorageStatus> {
    return this.request<ChatStorageStatus>("/api/chat/storage-status");
  }

  async configureChatStorage(postgres_url: string): Promise<{
    success: boolean;
    engine: "postgresql" | "sqlite";
    message: string;
    error?: string;
  }> {
    return this.request<{
      success: boolean;
      engine: "postgresql" | "sqlite";
      message: string;
      error?: string;
    }>("/api/chat/storage-config", {
      method: "POST",
      body: JSON.stringify({ postgres_url }),
    });
  }

  // ===== Collections =====
  async listCollections(): Promise<MemoryCollection[]> {
    return this.request<MemoryCollection[]>("/api/collections");
  }

  async createCollection(data: {
    name: string;
    description?: string;
    color?: string;
    icon?: string;
  }): Promise<MemoryCollection> {
    return this.request<MemoryCollection>("/api/collections", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getCollection(id: string): Promise<MemoryCollection> {
    return this.request<MemoryCollection>(`/api/collections/${id}`);
  }

  async addMemoryToCollection(collectionId: string, memoryId: string): Promise<void> {
    await this.request<void>(`/api/collections/${collectionId}/memories`, {
      method: "POST",
      body: JSON.stringify({ memory_id: memoryId }),
    });
  }

  async removeMemoryFromCollection(collectionId: string, memoryId: string): Promise<void> {
    await this.request<void>(`/api/collections/${collectionId}/memories/${memoryId}`, {
      method: "DELETE",
    });
  }

  async deleteCollection(id: string): Promise<void> {
    await this.request<void>(`/api/collections/${id}`, {
      method: "DELETE",
    });
  }

  // ===== Graph =====
  async getGraphData(params?: {
    entity_types?: string[];
    limit?: number;
    center_entity_id?: string;
  }): Promise<GraphData> {
    const query = new URLSearchParams();
    if (params?.entity_types)
      query.set("entity_types", params.entity_types.join(","));
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.center_entity_id)
      query.set("center_entity_id", params.center_entity_id);
    const qs = query.toString();
    return this.request<GraphData>(`/api/graph${qs ? `?${qs}` : ""}`);
  }

  async getNodeDetail(nodeId: string): Promise<{
    id: string;
    label: string;
    type: string;
    mention_count: number;
    file_type?: string;
    original_path?: string;
    created_at?: string;
    first_seen?: string;
    last_seen?: string;
    memories: Array<{ id: string; content: string; timestamp: string; summary?: string }>;
    connections: Array<{ id: string; label: string; relationship: string; type: string }>;
  }> {
    return this.request(`/api/graph/node/${nodeId}`);
  }

  async quickCapture(data: { content: string; title?: string; tags?: string[] }): Promise<Document> {
    return this.request<Document>("/api/documents/quick-capture", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async exportAll(): Promise<any> {
    return this.request("/api/documents/export/all");
  }

  async getEntity(id: string): Promise<Entity & { memories: Memory[] }> {
    return this.request<Entity & { memories: Memory[] }>(
      `/api/graph/entities/${id}`
    );
  }

  async getGraphStats(): Promise<{
    total_nodes: number;
    total_edges: number;
    entity_type_counts: Record<string, number>;
  }> {
    return this.request(`/api/graph/stats`);
  }

  // ===== Stats =====
  async getStats(): Promise<Stats> {
    return this.request<Stats>("/api/stats");
  }

  async getDailyDigest(): Promise<{
    date: string;
    summary: string;
    highlights: string[];
    memories_today_count: number;
    top_entities: Array<{ entity_name: string; entity_type: string }>;
  }> {
    return this.request("/api/stats/daily-digest");
  }

  async getActivity(limit?: number): Promise<ActivityItem[]> {
    const query = limit ? `?limit=${limit}` : "";
    return this.request<ActivityItem[]>(`/api/stats/activity${query}`);
  }

  async getTimeline(params?: {
    start_date?: string;
    end_date?: string;
    page?: number;
    per_page?: number;
  }): Promise<PaginatedResponse<TimelineEntry>> {
    const query = new URLSearchParams();
    if (params?.start_date) query.set("start_date", params.start_date);
    if (params?.end_date) query.set("end_date", params.end_date);
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    const qs = query.toString();
    return this.request<PaginatedResponse<TimelineEntry>>(
      `/api/stats/timeline${qs ? `?${qs}` : ""}`
    );
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export const api = new ApiClient();
export default api;
