import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Brain, Filter, Search } from "lucide-react";
import { api } from "@/lib/api";
import MemoryCard from "@/components/MemoryCard";
import EmptyState from "@/components/EmptyState";
import type { Memory } from "@/types";

export const MemoriesPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialSearch = searchParams.get("q") || "";
  const [memories, setMemories] = useState<Memory[]>([]);
  const [search, setSearch] = useState(initialSearch);
  const [selectedType, setSelectedType] = useState<string>("all");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (initialSearch) {
      setSearch(initialSearch);
    }
  }, [initialSearch]);

  const loadMemories = async () => {
    setIsLoading(true);
    try {
      const res = await api.listMemories({
        search: search.trim() || undefined,
        type: selectedType === "all" ? undefined : selectedType,
        per_page: 50,
      });
      const items = (res as any)?.items || res || [];
      setMemories(Array.isArray(items) ? items : []);
    } catch {
      setMemories([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(loadMemories, 250);
    return () => clearTimeout(timer);
  }, [search, selectedType]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">All Memories</h1>
          <p className="text-xs text-text-secondary">
            Browse through all extracted concepts, chunks, and multimodal memories
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-text-tertiary" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter memories..."
              className="pl-9 pr-4 py-2 bg-surface border border-border focus:border-primary rounded-lg text-xs text-text-primary placeholder:text-text-tertiary outline-none w-64"
            />
          </div>

          <div className="flex items-center gap-1.5 bg-surface border border-border rounded-lg px-2 py-1">
            <Filter className="w-3.5 h-3.5 text-text-tertiary" />
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-transparent text-xs text-text-secondary focus:outline-none"
            >
              <option value="all">All Types</option>
              <option value="text">Text / Notes</option>
              <option value="pdf">PDF Documents</option>
              <option value="image">Images / OCR</option>
              <option value="webpage">Webpages</option>
            </select>
          </div>
        </div>
      </div>

      {memories.length === 0 && !isLoading ? (
        <EmptyState
          icon={Brain}
          title="No memories match your query"
          description="Try removing your search filter or add more documents to ContextOS."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {memories.map((mem) => (
            <MemoryCard key={mem.id} memory={mem} />
          ))}
        </div>
      )}
    </div>
  );
};

export default MemoriesPage;
