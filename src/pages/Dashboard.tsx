import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Brain, FileText, FolderPlus, GitBranch, Search, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/app";
import StatCard from "@/components/StatCard";
import MemoryCard from "@/components/MemoryCard";
import AddSourceDialog from "@/components/AddSourceDialog";
import EmptyState from "@/components/EmptyState";
import type { Memory, Source } from "@/types";

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { stats, updateStats } = useAppStore();
  const [recentMemories, setRecentMemories] = useState<Memory[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [dailyDigest, setDailyDigest] = useState<{
    date: string;
    summary: string;
    highlights: string[];
    memories_today_count: number;
  } | null>(null);
  const [isAddSourceOpen, setIsAddSourceOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [statsData, memoriesData, sourcesData, digestData] = await Promise.allSettled([
        api.getStats(),
        api.listMemories({ page: 1, per_page: 3 }),
        api.listSources(),
        api.getDailyDigest(),
      ]);

      if (statsData.status === "fulfilled") {
        updateStats(statsData.value);
      }
      if (memoriesData.status === "fulfilled") {
        const items = (memoriesData.value as any)?.items || (memoriesData.value as any) || [];
        setRecentMemories(Array.isArray(items) ? items.slice(0, 3) : []);
      }
      if (sourcesData.status === "fulfilled") {
        setSources(sourcesData.value || []);
      }
      if (digestData.status === "fulfilled") {
        setDailyDigest(digestData.value);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/ask?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6 animate-fade-in">
      {/* Welcome & Global Ask */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="max-w-2xl space-y-3">
          <p className="text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
            Personal Memory Engine
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-text-primary">
            What are you looking for?
          </h1>
          <p className="text-xs text-text-secondary leading-relaxed">
            Recall across screenshots, research documents, and past conversations through
            associative memory.
          </p>

          <form onSubmit={handleSearchSubmit} className="pt-1">
            <div className="relative flex items-center">
              <Search className="w-4 h-4 absolute left-3.5 text-text-tertiary" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Ask anything... e.g. 'Where did I read about temporal knowledge graphs?'"
                className="w-full pl-10 pr-24 py-2.5 bg-background border border-border focus:border-border-hover rounded-lg text-text-primary text-xs outline-none transition-colors"
              />
              <button
                type="submit"
                className="absolute right-1.5 px-3 py-1.5 bg-text-primary hover:opacity-90 text-background text-xs font-medium rounded transition-opacity"
              >
                Recall
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          icon={Brain}
          label="Total Memories"
          value={stats?.total_memories ?? 0}
        />
        <StatCard
          icon={FileText}
          label="Documents Ingested"
          value={stats?.total_documents ?? 0}
        />
        <StatCard
          icon={GitBranch}
          label="Graph Entities"
          value={stats?.total_entities ?? 0}
        />
        <StatCard
          icon={FolderPlus}
          label="Monitored Sources"
          value={stats?.total_sources ?? sources.length}
        />
      </div>

      {/* Automatic Daily Memory Digest */}
      {dailyDigest && (
        <div className="rounded-xl border border-border bg-surface/50 p-5 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-semibold text-text-primary">
                  Daily Briefing
                </h3>
                <span className="text-[10px] text-text-tertiary font-mono">
                  {dailyDigest.date}
                </span>
              </div>
              <p className="text-xs text-text-secondary leading-relaxed mt-1">
                {dailyDigest.summary}
              </p>
            </div>

            <button
              onClick={() => navigate(`/ask?q=${encodeURIComponent("Give me a comprehensive summary of everything I worked on and learned today.")}`)}
              className="px-2.5 py-1 bg-surface-active hover:bg-surface-hover text-text-primary border border-border rounded text-[11px] font-medium transition-colors shrink-0"
            >
              Discuss Today's Work
            </button>
          </div>

          <div className="flex flex-wrap gap-1.5 pt-2 border-t border-border/50 text-[11px]">
            {dailyDigest.highlights.map((h, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded bg-surface border border-border text-text-secondary text-[11px]"
              >
                {h}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recent Memories Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold text-text-primary">Recent Memories</h2>
            <p className="text-xs text-text-secondary">
              Continuously ingested and connected from your authorized sources
            </p>
          </div>
          <button
            onClick={() => navigate("/memories")}
            className="text-xs font-medium text-primary hover:text-primary-hover transition-colors"
          >
            View all memories →
          </button>
        </div>

        {recentMemories.length === 0 && !isLoading ? (
          <EmptyState
            icon={Brain}
            title="No memories recorded yet"
            description="Authorize a folder or install the browser extension to let ContextOS begin building your personal knowledge base."
            actionLabel="Add First Monitored Folder"
            onAction={() => setIsAddSourceOpen(true)}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentMemories.map((mem) => (
              <MemoryCard key={mem.id} memory={mem} />
            ))}
          </div>
        )}
      </div>

      <AddSourceDialog
        isOpen={isAddSourceOpen}
        onClose={() => setIsAddSourceOpen(false)}
        onSourceAdded={loadData}
      />
    </div>
  );
};

export default Dashboard;
