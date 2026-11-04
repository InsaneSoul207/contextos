import React, { useEffect, useState } from "react";
import { Chrome, FolderOpen, FolderPlus, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import SourceCard from "@/components/SourceCard";
import AddSourceDialog from "@/components/AddSourceDialog";
import EmptyState from "@/components/EmptyState";
import { useAppStore } from "@/store/app";
import type { Source } from "@/types";

export const SourcesPage: React.FC = () => {
  const [sources, setSources] = useState<Source[]>([]);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { fetchStats } = useAppStore();

  const loadSources = async () => {
    setIsLoading(true);
    try {
      const data = await api.listSources();
      setSources(data || []);
    } catch {
      setSources([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handlePause = async (id: string) => {
    try {
      await api.updateSource(id, { status: "paused" });
      loadSources();
    } catch {}
  };

  const handleResume = async (id: string) => {
    try {
      await api.updateSource(id, { status: "active" });
      loadSources();
    } catch {}
  };

  const handleDelete = async (id: string) => {
    // Optimistic immediate UI update
    setSources((prev) => prev.filter((s) => s.id !== id));
    try {
      await api.deleteSource(id);
      await loadSources();
      fetchStats();
    } catch (err) {
      console.error("Failed to delete source:", err);
      loadSources();
    }
  };

  const handleSync = async (id: string) => {
    try {
      await api.syncSource(id);
      loadSources();
    } catch {}
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Connected Sources</h1>
          <p className="text-xs text-text-secondary">
            Authorized directories and extensions monitored by ContextOS
          </p>
        </div>

        <button
          onClick={() => setIsAddOpen(true)}
          className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-colors"
        >
          <FolderPlus className="w-4 h-4" />
          Add Monitored Folder
        </button>
      </div>

      {/* Browser Extension Status Banner */}
      <div className="p-5 rounded-xl border border-border bg-gradient-to-r from-surface to-surface-hover flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400">
            <Chrome className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Companion Browser Extension</h3>
            <p className="text-xs text-text-secondary">
              Save webpages, articles, and text selections directly to memory while browsing.
            </p>
          </div>
        </div>
        <div className="text-xs text-text-tertiary font-mono bg-background px-3 py-1.5 rounded border border-border">
          Port: 44480 (Listening)
        </div>
      </div>

      {/* Sources Grid */}
      {sources.length === 0 && !isLoading ? (
        <EmptyState
          icon={FolderOpen}
          title="No folders monitored yet"
          description="ContextOS requires explicit authorization before monitoring local directories."
          actionLabel="Authorise a Directory"
          onAction={() => setIsAddOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sources.map((src) => (
            <SourceCard
              key={src.id}
              source={src}
              onPause={handlePause}
              onResume={handleResume}
              onDelete={handleDelete}
              onSync={handleSync}
            />
          ))}
        </div>
      )}

      <AddSourceDialog
        isOpen={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        onSourceAdded={loadSources}
      />
    </div>
  );
};

export default SourcesPage;
