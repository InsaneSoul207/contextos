import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  FileText,
  Image,
  Code,
  FileVideo,
  FileAudio,
  Globe,
  Camera,
  File,
} from "lucide-react";
import { cn, formatRelativeDate, truncateText, getFileTypeIcon } from "@/lib/utils";
import type { Memory } from "@/types";

const iconMap = {
  FileText,
  Image,
  Code,
  FileVideo,
  FileAudio,
  Globe,
  Camera,
  File,
};

const typeColors: Record<string, string> = {
  text: "bg-surface-active text-text-secondary border border-border",
  image: "bg-surface-active text-text-secondary border border-border",
  code: "bg-surface-active text-text-secondary border border-border",
  note: "bg-surface-active text-text-secondary border border-border",
  conversation: "bg-surface-active text-text-secondary border border-border",
  web_page: "bg-surface-active text-text-secondary border border-border",
  screenshot: "bg-surface-active text-text-secondary border border-border",
};

interface MemoryCardProps {
  memory: Memory;
  className?: string;
}

export default function MemoryCard({ memory, className }: MemoryCardProps) {
  const navigate = useNavigate();
  const iconName = getFileTypeIcon(memory.file_type || memory.memory_type);
  const Icon = iconMap[iconName] || FileText;

  const confidence = memory.confidence ?? 1.0;
  const confidenceColor =
    confidence >= 0.8
      ? "text-success"
      : confidence >= 0.5
        ? "text-warning"
        : "text-danger";

  const displayTitle =
    memory.title ||
    (memory.filepath ? memory.filepath.split(/[/\\]/).pop() : "") ||
    memory.content?.slice(0, 40) ||
    "Memory Record";

  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15 }}
      onClick={() => navigate(`/memories/${memory.id}`)}
      className={cn(
        "group cursor-pointer rounded-xl border border-border bg-surface p-4 transition-colors hover:border-border-hover hover:bg-surface-hover",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-surface-active flex items-center justify-center flex-shrink-0">
            <Icon className="w-4 h-4 text-text-secondary" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-medium text-text-primary truncate group-hover:text-black transition-colors">
              {displayTitle}
            </h3>
            <p className="text-xs text-text-tertiary truncate mt-0.5">
              {memory.filepath || "Local Storage"}
            </p>
          </div>
        </div>
      </div>

      {/* Content Preview */}
      {memory.content && (
        <p className="text-sm text-text-secondary leading-relaxed mb-3">
          {truncateText(memory.content, 120)}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "text-[11px] px-2 py-0.5 rounded-full border font-medium capitalize",
              typeColors[memory.memory_type] || "bg-surface-active text-text-secondary border-border"
            )}
          >
            {memory.memory_type || "text"}
          </span>
          <span className={cn("text-[11px] font-mono", confidenceColor)}>
            {Math.round(confidence * 100)}%
          </span>
        </div>
        <span className="text-[11px] text-text-tertiary">
          {formatRelativeDate(memory.created_at || (memory as any).timestamp || new Date().toISOString())}
        </span>
      </div>
    </motion.div>
  );
}
