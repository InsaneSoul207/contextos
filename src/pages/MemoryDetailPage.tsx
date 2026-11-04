import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Brain, Calendar, FileText, GitBranch, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatRelativeDate } from "@/lib/utils";
import type { Memory } from "@/types";

export const MemoryDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [memory, setMemory] = useState<Memory | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const fetchMemory = async () => {
      setIsLoading(true);
      try {
        const data = await api.getMemory(id);
        setMemory(data);
      } catch {
        setMemory(null);
      } finally {
        setIsLoading(false);
      }
    };
    fetchMemory();
  }, [id]);

  const handleDelete = async () => {
    if (!id || !confirm("Are you sure you want to delete this memory?")) return;
    try {
      await api.deleteMemory(id);
      navigate("/memories");
    } catch {}
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-text-tertiary">
        Loading memory details...
      </div>
    );
  }

  if (!memory) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-text-secondary">Memory not found.</p>
        <button
          onClick={() => navigate("/memories")}
          className="text-xs text-primary hover:underline"
        >
          Return to Memories
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <button
          onClick={handleDelete}
          className="inline-flex items-center gap-1 text-xs text-danger hover:text-danger/80 transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete Memory
        </button>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-primary/10 border border-primary/20 text-primary">
            <Brain className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary">{memory.title || "Memory Record"}</h1>
            <div className="flex items-center gap-4 text-xs text-text-tertiary mt-1">
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {formatRelativeDate(memory.created_at)}
              </span>
              <span className="capitalize px-2 py-0.5 rounded bg-surface border border-border">
                {memory.memory_type}
              </span>
            </div>
          </div>
        </div>

        {/* Content Box */}
        <div className="p-6 rounded-xl border border-border bg-surface shadow-sm space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
            Extracted Content
          </h2>
          <div className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
            {memory.content}
          </div>
        </div>

        {/* Source File Info */}
        <div className="p-6 rounded-xl border border-border bg-surface shadow-sm space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
            Source Provenance
          </h2>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-text-tertiary block">File Type</span>
              <span className="font-mono text-text-secondary uppercase">{memory.file_type}</span>
            </div>
            <div>
              <span className="text-text-tertiary block">Original Path</span>
              <span className="font-mono text-text-secondary truncate block">{memory.filepath || "Local Storage"}</span>
            </div>
          </div>
        </div>

        {/* Connected Graph Entities */}
        {memory.entities && memory.entities.length > 0 && (
          <div className="p-6 rounded-xl border border-border bg-surface shadow-sm space-y-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-primary" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                Connected Entities
              </h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {memory.entities.map((ent) => (
                <span
                  key={ent.id}
                  className="px-2.5 py-1 rounded-md bg-surface-hover border border-border text-xs text-text-primary"
                >
                  {ent.name} <span className="text-text-tertiary text-[10px]">({ent.entity_type})</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MemoryDetailPage;
