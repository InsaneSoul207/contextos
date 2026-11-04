import { useState } from "react";
import { motion } from "framer-motion";
import {
  FolderOpen,
  Pause,
  Play,
  Trash2,
  RefreshCw,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn, formatRelativeDate } from "@/lib/utils";
import type { Source } from "@/types";

const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: "bg-success", label: "Active" },
  paused: { color: "bg-warning", label: "Paused" },
  error: { color: "bg-danger", label: "Error" },
  syncing: { color: "bg-primary", label: "Syncing" },
};

interface SourceCardProps {
  source: Source;
  onPause?: (id: string) => void;
  onResume?: (id: string) => void;
  onDelete?: (id: string) => void;
  onSync?: (id: string) => void;
}

export default function SourceCard({
  source,
  onPause,
  onResume,
  onDelete,
  onSync,
}: SourceCardProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const status = statusConfig[source.status] || statusConfig.active;

  return (
    <motion.div
      whileHover={{ y: -1 }}
      transition={{ duration: 0.15 }}
      className="rounded-xl border border-border bg-surface p-4 transition-colors hover:border-border-hover group"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-primary-muted flex items-center justify-center flex-shrink-0">
            <FolderOpen className="w-5 h-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-medium text-text-primary truncate">
              {source.display_name}
            </h3>
            <p className="text-xs text-text-tertiary truncate mt-0.5 font-mono">
              {source.path}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <div className={cn("w-2 h-2 rounded-full", status.color)} />
          <span className="text-xs text-text-secondary">{status.label}</span>
        </div>
      </div>

      {/* Info Row */}
      <div className="flex items-center gap-4 text-xs text-text-tertiary mb-3">
        <span>{source.file_count} files</span>
        <span>·</span>
        <span className="capitalize">{source.source_type}</span>
        {source.last_synced && (
          <>
            <span>·</span>
            <span>Synced {formatRelativeDate(source.last_synced)}</span>
          </>
        )}
      </div>

      {/* Error Message */}
      {source.status === "error" && (
        <div className="flex items-center gap-2 text-xs text-danger bg-danger/10 rounded-lg px-3 py-2 mb-3">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Source encountered an error during last sync</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-border">
        {source.status === "active" ? (
          <button
            onClick={() => onPause?.(source.id)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
          >
            <Pause className="w-3.5 h-3.5" /> Pause
          </button>
        ) : source.status === "paused" ? (
          <button
            onClick={() => onResume?.(source.id)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
          >
            <Play className="w-3.5 h-3.5" /> Resume
          </button>
        ) : null}

        <button
          onClick={() => onSync?.(source.id)}
          disabled={source.status === "syncing"}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          {source.status === "syncing" ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          Sync
        </button>

        <div className="flex-1" />

        {confirmDelete ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-danger">Delete?</span>
            <button
              onClick={() => {
                onDelete?.(source.id);
                setConfirmDelete(false);
              }}
              className="px-2 py-1 text-xs bg-danger/10 text-danger rounded hover:bg-danger/20 transition-colors"
            >
              Yes
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="px-2 py-1 text-xs text-text-secondary rounded hover:bg-surface-hover transition-colors"
            >
              No
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-text-tertiary hover:text-danger hover:bg-danger/10 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </motion.div>
  );
}
