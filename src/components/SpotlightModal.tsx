import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Brain,
  FileText,
  Sparkles,
  ArrowRight,
  CornerDownLeft,
  X,
  Layers,
  Calendar,
  ExternalLink,
  Cpu,
  Image as ImageIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, formatRelativeDate, getEntityTypeColor } from "@/lib/utils";
import type { SearchResult } from "@/types";

interface SpotlightModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SpotlightModal: React.FC<SpotlightModalProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus on open & reset
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(0);
    } else {
      setQuery("");
      setResults([]);
    }
  }, [isOpen]);

  // Search debouncing
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    const timeout = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await api.search(q, { limit: 8 });
        setResults(res.results || []);
        setSelectedIndex(0);
      } catch (err) {
        console.error("Spotlight search error:", err);
      } finally {
        setIsLoading(false);
      }
    }, 180);

    return () => clearTimeout(timeout);
  }, [query]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
      return;
    }

    const totalItems = results.length + 1; // +1 for "Ask AI" action

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % totalItems);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + totalItems) % totalItems);
    } else if (e.key === "Enter") {
      e.preventDefault();
      handleSelectIndex(selectedIndex);
    }
  };

  const handleSelectIndex = (index: number) => {
    if (index === 0 && results.length > 0) {
      // Open the top result
      const top = results[0];
      navigate(`/memories/${top.memory.id}`);
      onClose();
    } else if (index < results.length) {
      const item = results[index];
      navigate(`/memories/${item.memory.id}`);
      onClose();
    } else {
      // Ask ContextOS query
      const q = query.trim();
      if (q) {
        navigate(`/ask?q=${encodeURIComponent(q)}`);
        onClose();
      }
    }
  };

  if (!isOpen) return null;

  const selectedItem = results[selectedIndex] || null;
  const isAskAISelected = selectedIndex === results.length;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center pt-[14vh] bg-black/35 backdrop-blur-sm animate-in fade-in duration-150 p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
        className="w-full max-w-3xl bg-[#faf8f5] border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col ring-1 ring-border animate-in zoom-in-95 duration-150"
        style={{ maxHeight: "600px" }}
      >
        {/* Spotlight Input Header */}
        <div className="h-14 px-5 border-b border-border flex items-center gap-3 shrink-0 bg-surface">
          <Search className="w-4 h-4 text-text-tertiary shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type to search memories, notes, or files..."
            className="w-full bg-transparent border-none outline-none text-sm text-text-primary placeholder:text-text-tertiary tracking-normal font-normal"
          />
          {isLoading && (
            <div className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin shrink-0" />
          )}
          <kbd className="px-1.5 py-0.5 rounded bg-surface-hover border border-border text-text-tertiary text-[10px] font-mono shrink-0">
            ESC
          </kbd>
        </div>

        {/* Spotlight Split Layout: Left Results + Right Preview */}
        <div className="flex-1 flex min-h-[320px] max-h-[440px] overflow-hidden divide-x divide-border">
          {/* Left: Results List */}
          <div className="w-[55%] overflow-y-auto p-2 space-y-1">
            {/* Ask AI Option Always Visible if query is present */}
            {query.trim() && (
              <div
                onClick={() => handleSelectIndex(results.length)}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors",
                  isAskAISelected
                    ? "bg-surface text-text-primary font-medium border border-border shadow-xs"
                    : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                )}
              >
                <div className="w-6 h-6 rounded-md bg-surface-hover border border-border flex items-center justify-center text-[10px] font-semibold text-text-primary shrink-0">
                  AI
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-xs text-text-primary">
                    <span>Ask ContextOS AI</span>
                  </div>
                  <p className="text-[10px] text-text-tertiary truncate">
                    "{query}"
                  </p>
                </div>
                <CornerDownLeft className="w-3.5 h-3.5 opacity-60 text-text-tertiary" />
              </div>
            )}

            {results.length > 0 ? (
              results.map((res, idx) => {
                const isSelected = selectedIndex === idx;
                const mem = res.memory;
                const isImage = mem.file_type === "png" || mem.file_type === "jpg" || mem.memory_type === "image";
                const Icon = isImage ? ImageIcon : FileText;

                return (
                  <div
                    key={mem.id}
                    onClick={() => handleSelectIndex(idx)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={cn(
                      "flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors group",
                      isSelected
                        ? "bg-surface text-text-primary font-medium border border-border shadow-xs"
                        : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                    )}
                  >
                    <div className="w-6 h-6 rounded-md bg-surface-hover border border-border flex items-center justify-center text-text-tertiary shrink-0">
                      <Icon className="w-3.5 h-3.5" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs text-text-primary">
                        {mem.title || mem.filepath?.split(/[\\/]/).pop() || "Document Memory"}
                      </p>
                      <p className="text-[10px] text-text-tertiary truncate">
                        {mem.summary || mem.content}
                      </p>
                    </div>

                    <span className="text-[10px] font-mono text-text-tertiary shrink-0">
                      {Math.round(res.score * 100)}%
                    </span>
                  </div>
                );
              })
            ) : !query.trim() ? (
              <div className="p-8 text-center text-xs text-text-tertiary space-y-1">
                <p className="text-text-primary font-medium">Quick Recall</p>
                <p className="text-[11px] text-text-tertiary">
                  Press <kbd className="px-1.5 py-0.5 rounded bg-surface-hover border border-border text-text-secondary font-mono">Alt + Space</kbd> or <kbd className="px-1.5 py-0.5 rounded bg-surface-hover border border-border text-text-secondary font-mono">Ctrl + K</kbd> to search.
                </p>
              </div>
            ) : !isLoading ? (
              <div className="p-8 text-center text-xs text-text-tertiary">
                No memories found for "{query}".
              </div>
            ) : null}
          </div>

          {/* Right: macOS Style Preview Pane */}
          <div className="w-[45%] bg-[#f5f1e8] p-5 overflow-y-auto flex flex-col justify-between space-y-4">
            {selectedItem ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-[11px] text-text-tertiary">
                  <span className="uppercase font-medium text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary">
                    {selectedItem.memory.memory_type}
                  </span>
                  <span className="font-mono">
                    Match: {Math.round(selectedItem.score * 100)}%
                  </span>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-text-primary leading-snug">
                    {selectedItem.memory.title ||
                      selectedItem.memory.filepath?.split(/[\\/]/).pop()}
                  </h4>
                  <p className="text-[10px] text-text-tertiary mt-0.5 truncate font-mono">
                    {selectedItem.memory.filepath}
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-surface border border-border text-xs text-text-secondary leading-relaxed max-h-48 overflow-y-auto shadow-xs">
                  {selectedItem.memory.summary || selectedItem.memory.content}
                </div>
              </div>
            ) : isAskAISelected ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-4 space-y-2">
                <div className="w-8 h-8 rounded-md bg-surface border border-border flex items-center justify-center text-xs font-semibold text-text-primary shadow-xs">
                  AI
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-text-primary">Ask ContextOS</h4>
                  <p className="text-[11px] text-text-tertiary mt-1">
                    Synthesizes evidence from your indexed files and answers directly.
                  </p>
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center text-xs text-text-tertiary">
                <FileText className="w-6 h-6 text-text-tertiary/40 mb-1.5" />
                <span>Select an item to view preview</span>
              </div>
            )}

            {/* Bottom Keyboard Hint */}
            <div className="pt-3 border-t border-border flex items-center justify-between text-[10px] text-text-tertiary">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">↑↓</kbd> Navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">↵</kbd> Open
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-surface border border-border text-text-secondary font-mono">Esc</kbd> Close
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SpotlightModal;
