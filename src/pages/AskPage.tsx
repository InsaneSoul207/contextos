import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ArrowUp,
  Brain,
  ChevronLeft,
  ChevronRight,
  Database,
  HelpCircle,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  Check,
  AlertCircle,
  Settings,
} from "lucide-react";
import { api } from "@/lib/api";
import ChatMessage from "@/components/ChatMessage";
import { cn, formatRelativeDate } from "@/lib/utils";
import type {
  ChatMessage as ChatMessageType,
  Conversation,
  ChatStorageStatus,
} from "@/types";

const SUGGESTIONS = [
  "What do I know about diffusion models?",
  "Show me everything related to Transformers.",
  "Which document contains my project architecture?",
  "When did I first save information about attention mechanisms?",
];

export const AskPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  // Multi-session State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [storageStatus, setStorageStatus] = useState<ChatStorageStatus | null>(null);
  const [isConfiguringDb, setIsConfiguringDb] = useState(false);
  const [postgresInputUrl, setPostgresInputUrl] = useState("");
  const [dbConfigMessage, setDbConfigMessage] = useState<{ text: string; error?: boolean } | null>(null);

  // Chat State
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDeletingId, setIsDeletingId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isSendingRef = useRef(false);
  const lastHandledQuery = useRef<string>("");

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Load conversation list and storage status on mount
  const loadConversations = async (autoSelectLatest = false) => {
    try {
      const [convList, status] = await Promise.all([
        api.listConversations(50),
        api.getChatStorageStatus(),
      ]);
      setConversations(convList);
      setStorageStatus(status);

      if (autoSelectLatest && convList.length > 0 && !activeConversationId) {
        selectConversation(convList[0].id);
      }
    } catch (err) {
      console.error("Failed to load conversations or storage status:", err);
    }
  };

  useEffect(() => {
    loadConversations(false);
  }, []);

  // Load specific conversation messages
  const selectConversation = async (convId: string) => {
    if (activeConversationId === convId) return;
    setActiveConversationId(convId);
    setIsLoading(true);
    try {
      const detail = await api.getConversation(convId);
      if (detail && detail.messages) {
        setMessages(detail.messages);
      }
    } catch (err: any) {
      console.error("Failed to load conversation history:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Start a fresh new chat session
  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setInput("");
    inputRef.current?.focus();
  };

  // Delete a conversation thread
  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    setIsDeletingId(convId);
    try {
      await api.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConversationId === convId) {
        handleNewChat();
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    } finally {
      setIsDeletingId(null);
    }
  };

  // Send message with context memory
  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText ?? input).trim();
    if (!textToSend || isSendingRef.current) return;

    isSendingRef.current = true;
    setIsLoading(true);

    const userMessage: ChatMessageType = {
      id: String(Date.now()),
      role: "user",
      content: textToSend,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await api.chat(textToSend, activeConversationId || undefined);
      const content =
        response?.message?.content ||
        response?.answer ||
        "I couldn't find any relevant memories matching your query.";
      const msgId = response?.message?.id || String(Date.now() + 1);
      const sources = response?.sources || [];

      const assistantMessage: ChatMessageType = {
        id: msgId,
        role: "assistant",
        content,
        sources,
        timestamp: response?.message?.timestamp || new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // If this was a new conversation, update activeConversationId and reload sidebar
      if (response?.conversation_id) {
        setActiveConversationId(response.conversation_id);
      }
      loadConversations(false);
    } catch (err: any) {
      const errorMessage: ChatMessageType = {
        id: String(Date.now() + 1),
        role: "assistant",
        content: `Error retrieving memory: ${err?.message || "Could not reach backend service."}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      isSendingRef.current = false;
      setIsLoading(false);
    }
  };

  // Auto-run initial query from URL search param if present (e.g. from top search bar or Knowledge Graph)
  useEffect(() => {
    const q = initialQuery.trim();
    if (q && q !== lastHandledQuery.current) {
      lastHandledQuery.current = q;
      handleSend(q);
      setSearchParams({}, { replace: true });
    }
  }, [initialQuery]);

  // Handle postgres quick-config save
  const handleSavePostgres = async () => {
    setDbConfigMessage(null);
    try {
      const res = await api.configureChatStorage(postgresInputUrl);
      if (res.success) {
        setDbConfigMessage({ text: res.message, error: false });
        const updatedStatus = await api.getChatStorageStatus();
        setStorageStatus(updatedStatus);
        setTimeout(() => setIsConfiguringDb(false), 1500);
      } else {
        setDbConfigMessage({ text: res.message || res.error || "Connection failed", error: true });
      }
    } catch (err: any) {
      setDbConfigMessage({ text: err?.message || "Connection failed", error: true });
    }
  };

  const activeConv = conversations.find((c) => c.id === activeConversationId);

  return (
    <div className="flex h-full w-full overflow-hidden bg-background relative">
      {/* ===== ChatGPT-Style Left Sidebar ===== */}
      <div
        className={cn(
          "h-full border-r border-border bg-surface/80 backdrop-blur-md flex flex-col transition-all duration-300 z-20 shrink-0",
          isSidebarOpen ? "w-64" : "w-0 border-r-0 overflow-hidden"
        )}
      >
        {/* Sidebar Header & + New Chat Button */}
        <div className="p-3 border-b border-border space-y-2">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Conversations
            </span>
            <button
              onClick={() => setIsSidebarOpen(false)}
              className="p-1 hover:bg-surface-hover rounded-md text-text-tertiary hover:text-text-primary transition-colors"
              title="Collapse sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={handleNewChat}
            className="w-full py-2 px-3 bg-surface-active hover:bg-surface-hover text-text-primary border border-border rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {conversations.length === 0 ? (
            <div className="p-4 text-center text-xs text-text-tertiary">
              No conversations yet.
            </div>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.id === activeConversationId;
              const isDeleting = isDeletingId === conv.id;
              return (
                <div
                  key={conv.id}
                  onClick={() => selectConversation(conv.id)}
                  className={cn(
                    "group relative flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition-colors",
                    isActive
                      ? "bg-surface text-text-primary font-medium border border-border shadow-xs"
                      : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                  )}
                >
                  <div className="min-w-0 pr-2">
                    <p className="truncate leading-tight font-medium">
                      {conv.title || "Untitled"}
                    </p>
                  </div>

                  {/* Delete button on hover */}
                  <button
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                    disabled={isDeleting}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-danger text-text-tertiary rounded transition-opacity shrink-0"
                    title="Delete"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ===== Main Chat Pane ===== */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden bg-background">
        {/* Chat Header Bar */}
        <div className="h-11 border-b border-border px-4 flex items-center justify-between bg-surface/40 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-1 hover:bg-surface-hover rounded text-text-secondary hover:text-text-primary transition-colors"
                title="Open conversations"
              >
                <PanelLeftOpen className="w-3.5 h-3.5" />
              </button>
            )}

            <h2 className="text-xs font-medium text-text-primary truncate">
              {activeConv?.title || "New Chat"}
            </h2>
          </div>

          <button
            onClick={handleNewChat}
            className="px-2 py-1 bg-surface hover:bg-surface-hover border border-border rounded text-[11px] text-text-secondary hover:text-text-primary transition-colors"
          >
            New
          </button>
        </div>

        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 max-w-2xl w-full mx-auto">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
              <div className="space-y-1">
                <h3 className="text-lg font-medium text-text-primary tracking-tight">
                  What would you like to recall?
                </h3>
                <p className="text-xs text-text-secondary">
                  Ask anything across your notes, documents, and past work.
                </p>
              </div>

              <div className="flex flex-wrap justify-center gap-1.5 max-w-md pt-2">
                {SUGGESTIONS.slice(0, 3).map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(suggestion)}
                    className="px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary bg-surface hover:bg-surface-hover border border-border rounded-full transition-colors text-left"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
          )}

          {isLoading && (
            <ChatMessage
              message={{
                id: "typing",
                role: "assistant",
                content: "",
                timestamp: new Date().toISOString(),
              }}
              isTyping={true}
            />
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Fixed Bottom Input Box */}
        <div className="p-4 bg-background border-t border-border/60 shrink-0">
          <div className="max-w-2xl mx-auto">
            <div className="relative flex items-end bg-surface border border-border rounded-xl shadow-xs focus-within:border-accent/70 transition-colors p-1.5">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask anything... (Enter to send)"
                rows={1}
                className="w-full max-h-36 resize-none bg-transparent px-3 py-2 text-xs sm:text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none leading-relaxed"
                style={{ minHeight: "40px" }}
              />

              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isLoading}
                className={cn(
                  "p-2 rounded-lg shrink-0 transition-opacity mb-0.5 mr-0.5",
                  input.trim() && !isLoading
                    ? "bg-primary text-surface hover:opacity-90"
                    : "bg-surface-hover text-text-tertiary cursor-not-allowed opacity-50"
                )}
                title="Send message"
              >
                <ArrowUp className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AskPage;
