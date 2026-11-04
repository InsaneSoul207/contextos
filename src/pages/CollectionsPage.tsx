import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Library,
  Plus,
  Folder,
  Sparkles,
  BookOpen,
  ArrowRight,
  Trash2,
  Brain,
  X,
  FileText,
  Calendar,
  Layers,
  Search,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, formatRelativeDate } from "@/lib/utils";
import type { MemoryCollection, Memory } from "@/types";

const COLOR_PALETTE = [
  "#27272a", // Zinc dark
  "#3f3f46", // Zinc medium
  "#52525b", // Zinc lighter
  "#475569", // Slate
  "#334155", // Slate dark
];

export const CollectionsPage: React.FC = () => {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<MemoryCollection[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Detail Modal State
  const [selectedCollection, setSelectedCollection] = useState<MemoryCollection | null>(null);
  const [collectionMemories, setCollectionMemories] = useState<Memory[]>([]);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailFilter, setDetailFilter] = useState("");

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newColor, setNewColor] = useState(COLOR_PALETTE[0]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadCollections = async () => {
    setIsLoading(true);
    try {
      const data = await api.listCollections();
      setCollections(data);
    } catch (err) {
      console.error("Failed to load collections:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCollections();
  }, []);

  const openCollection = async (col: MemoryCollection) => {
    setSelectedCollection(col);
    setIsLoadingDetail(true);
    setDetailFilter("");
    try {
      const detail = await api.getCollection(col.id);
      setCollectionMemories(detail.memories || []);
    } catch (err) {
      console.error("Failed to load collection details:", err);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const created = await api.createCollection({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        color: newColor,
        icon: "folder",
      });
      setCollections((prev) => [created, ...prev]);
      setIsCreateOpen(false);
      setNewName("");
      setNewDesc("");
      setNewColor(COLOR_PALETTE[0]);
    } catch (err) {
      console.error("Failed to create collection:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, colId: string) => {
    e.stopPropagation();
    try {
      await api.deleteCollection(colId);
      setCollections((prev) => prev.filter((c) => c.id !== colId));
      if (selectedCollection?.id === colId) {
        setSelectedCollection(null);
      }
    } catch (err) {
      console.error("Failed to delete collection:", err);
    }
  };

  const handleRemoveMemory = async (memoryId: string) => {
    if (!selectedCollection || selectedCollection.is_smart) return;
    try {
      await api.removeMemoryFromCollection(selectedCollection.id, memoryId);
      setCollectionMemories((prev) => prev.filter((m) => m.id !== memoryId));
      setCollections((prev) =>
        prev.map((c) =>
          c.id === selectedCollection.id
            ? { ...c, item_count: Math.max(0, c.item_count - 1) }
            : c
        )
      );
    } catch (err) {
      console.error("Failed to remove memory:", err);
    }
  };

  const handleAskAboutCollection = (colName: string) => {
    navigate(`/ask?q=${encodeURIComponent(`What key knowledge and insights are in my "${colName}" collection?`)}`);
  };

  const smartCollections = collections.filter((c) => c.is_smart);
  const customCollections = collections.filter((c) => !c.is_smart);

  const filteredMemories = collectionMemories.filter((m) => {
    if (!detailFilter.trim()) return true;
    const q = detailFilter.toLowerCase();
    return (
      m.content.toLowerCase().includes(q) ||
      (m.summary && m.summary.toLowerCase().includes(q)) ||
      ((m as any).document_filename && (m as any).document_filename.toLowerCase().includes(q))
    );
  });

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 animate-fade-in relative min-h-full">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-text-primary">
            Memory Collections
          </h1>
          <p className="text-xs text-text-secondary mt-0.5">
            Thematic notebooks and project groupings
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="px-3 py-1.5 bg-text-primary hover:opacity-90 text-background rounded-lg text-xs font-medium flex items-center gap-1.5 transition-opacity"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Collection</span>
        </button>
      </div>

      {/* Section 1: Smart Auto-Curated Collections */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-medium uppercase tracking-wider text-text-tertiary">
            Monitored Source Groups
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {smartCollections.map((col) => (
            <div
              key={col.id}
              onClick={() => openCollection(col)}
              className="group p-4 rounded-xl bg-surface border border-border hover:border-border-hover cursor-pointer transition-colors"
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="text-sm font-medium text-text-primary group-hover:text-black transition-colors truncate">
                  {col.name}
                </h3>
                <span className="text-[10px] text-text-tertiary px-1.5 py-0.5 rounded bg-surface-active border border-border">
                  Auto
                </span>
              </div>

              <p className="text-xs text-text-tertiary line-clamp-2 min-h-[32px]">
                {col.description || "Monitored folder collection"}
              </p>

              <div className="flex items-center justify-between pt-3 mt-2 border-t border-border/50 text-xs text-text-tertiary">
                <span>{col.item_count} {col.item_count === 1 ? "memory" : "memories"}</span>
                <span className="text-text-secondary group-hover:text-text-primary transition-colors">Open</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 2: Custom Collections */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-medium uppercase tracking-wider text-text-tertiary">
            Custom Notebooks
          </h2>
          <span className="text-xs text-text-tertiary">
            {customCollections.length}
          </span>
        </div>

        {customCollections.length === 0 ? (
          <div className="p-6 border border-dashed border-border rounded-xl bg-surface/30 text-center space-y-2">
            <p className="text-xs font-medium text-text-secondary">No custom collections yet</p>
            <p className="text-[11px] text-text-tertiary">
              Group memories into custom notebooks for specific projects or topics.
            </p>
            <button
              onClick={() => setIsCreateOpen(true)}
              className="mt-1 px-3 py-1 bg-surface-active hover:bg-surface border border-border rounded-lg text-xs font-medium text-text-primary transition-colors"
            >
              Create collection
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {customCollections.map((col) => (
              <div
                key={col.id}
                onClick={() => openCollection(col)}
                className="group p-4 rounded-xl bg-surface border border-border hover:border-border-hover cursor-pointer transition-colors"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="text-sm font-medium text-text-primary group-hover:text-black transition-colors truncate">
                    {col.name}
                  </h3>

                  <button
                    onClick={(e) => handleDelete(e, col.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-text-tertiary rounded transition-all"
                    title="Delete notebook"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <p className="text-xs text-text-tertiary line-clamp-2 min-h-[32px]">
                  {col.description || "Custom personal collection"}
                </p>

                <div className="flex items-center justify-between pt-3 mt-2 border-t border-border/50 text-xs text-text-tertiary">
                  <span>{col.item_count} {col.item_count === 1 ? "memory" : "memories"}</span>
                  <span className="text-text-secondary group-hover:text-text-primary transition-colors">Open</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ===== Slide-over Collection Detail Drawer ===== */}
      {selectedCollection && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-xl h-full bg-surface border-l border-border flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-6 border-b border-border/80 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 min-w-0">
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 shadow-md"
                  style={{
                    backgroundColor: `${selectedCollection.color}25`,
                    color: selectedCollection.color,
                  }}
                >
                  <Folder className="w-6 h-6" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-lg font-bold text-text-primary truncate">
                    {selectedCollection.name}
                  </h2>
                  <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">
                    {selectedCollection.description || "Collection memories and evidence"}
                  </p>
                </div>
              </div>

              <button
                onClick={() => setSelectedCollection(null)}
                className="p-1.5 hover:bg-surface-hover rounded-lg text-text-tertiary hover:text-text-primary transition-colors shrink-0"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Quick Actions Bar */}
            <div className="px-6 py-3 border-b border-border/60 bg-surface-hover/20 flex items-center justify-between gap-3">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                <input
                  type="text"
                  value={detailFilter}
                  onChange={(e) => setDetailFilter(e.target.value)}
                  placeholder="Filter memories in collection..."
                  className="w-full pl-9 pr-3 py-1.5 bg-background border border-border rounded-xl text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-primary"
                />
              </div>

              <button
                onClick={() => handleAskAboutCollection(selectedCollection.name)}
                className="px-3 py-1.5 bg-primary hover:bg-primary-hover text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors shrink-0"
              >
                <Brain className="w-3.5 h-3.5" />
                <span>Ask AI</span>
              </button>
            </div>

            {/* Memories List */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {isLoadingDetail ? (
                <div className="flex items-center justify-center h-48 text-xs text-text-tertiary">
                  Loading collection memories...
                </div>
              ) : filteredMemories.length === 0 ? (
                <div className="text-center py-16 text-xs text-text-tertiary space-y-2">
                  <p>No memories found in this collection.</p>
                  {selectedCollection.is_smart && (
                    <p className="text-[11px] text-text-tertiary/80">
                      Files ingested from this folder will automatically appear here.
                    </p>
                  )}
                </div>
              ) : (
                filteredMemories.map((mem) => (
                  <div
                    key={mem.id}
                    className="p-4 rounded-xl bg-background border border-border/80 hover:border-primary/40 transition-colors space-y-2.5 relative group"
                  >
                    <div className="flex items-center justify-between text-[11px] text-text-tertiary">
                      <span className="flex items-center gap-1.5 font-medium text-text-secondary">
                        <FileText className="w-3.5 h-3.5 text-primary" />
                        {(mem as any).document_filename || "Document"}
                      </span>
                      <span className="font-mono">
                        {formatRelativeDate(mem.created_at || (mem as any).timestamp)}
                      </span>
                    </div>

                    <p className="text-xs text-text-primary leading-relaxed line-clamp-4">
                      {mem.summary || mem.content}
                    </p>

                    <div className="flex items-center justify-between pt-1 text-[10px]">
                      <span className="px-2 py-0.5 rounded bg-surface-active text-text-secondary capitalize font-medium">
                        {mem.memory_type}
                      </span>

                      {!selectedCollection.is_smart && (
                        <button
                          onClick={() => handleRemoveMemory(mem.id)}
                          className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-opacity"
                        >
                          Remove from collection
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ===== Create Collection Modal ===== */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-surface border border-border rounded-2xl shadow-2xl p-6 space-y-5 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold text-text-primary flex items-center gap-2">
                <Plus className="w-4 h-4 text-primary" />
                Create Memory Collection
              </h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="p-1 hover:bg-surface-hover rounded text-text-tertiary hover:text-text-primary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-secondary">Collection Name</label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. GeoBERT Change Detection, Thesis Research"
                  className="w-full px-3 py-2 bg-background border border-border rounded-xl text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-secondary">Description (Optional)</label>
                <textarea
                  rows={2}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Brief description of what this collection covers..."
                  className="w-full px-3 py-2 bg-background border border-border rounded-xl text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-primary resize-none"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-secondary">Accent Color</label>
                <div className="flex items-center gap-2.5">
                  {COLOR_PALETTE.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setNewColor(c)}
                      className={cn(
                        "w-6 h-6 rounded-full transition-transform",
                        newColor === c ? "scale-125 ring-2 ring-white shadow-md" : "hover:scale-110"
                      )}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 text-xs text-text-secondary hover:text-text-primary rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newName.trim() || isSubmitting}
                  className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-xl transition-colors shadow-sm disabled:opacity-50"
                >
                  {isSubmitting ? "Creating..." : "Create Collection"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default CollectionsPage;
