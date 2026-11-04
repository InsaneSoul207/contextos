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

interface TimelineItemProps {
  memory: Memory;
  isLast?: boolean;
  onClick?: (id: string) => void;
}

export default function TimelineItem({
  memory,
  isLast = false,
  onClick,
}: TimelineItemProps) {
  const iconName = getFileTypeIcon(memory.file_type);
  const Icon = iconMap[iconName];

  return (
    <div className="flex gap-4">
      {/* Timeline Connector */}
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-surface-active border border-border flex items-center justify-center flex-shrink-0 z-10">
          <Icon className="w-3.5 h-3.5 text-text-secondary" />
        </div>
        {!isLast && (
          <div className="w-px flex-1 bg-border min-h-[24px]" />
        )}
      </div>

      {/* Content */}
      <motion.div
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.2 }}
        onClick={() => onClick?.(memory.id)}
        className={cn(
          "flex-1 rounded-xl border border-border bg-surface p-4 mb-4 cursor-pointer transition-colors hover:border-border-hover hover:bg-surface-hover group",
          isLast && "mb-0"
        )}
      >
        <div className="flex items-start justify-between gap-3 mb-1.5">
          <h4 className="text-sm font-medium text-text-primary group-hover:text-primary-hover transition-colors truncate">
            {memory.title || memory.filepath.split("/").pop() || "Untitled"}
          </h4>
          <span className="text-[11px] text-text-tertiary flex-shrink-0">
            {formatRelativeDate(memory.created_at)}
          </span>
        </div>
        {memory.content && (
          <p className="text-xs text-text-secondary leading-relaxed mb-2">
            {truncateText(memory.content, 160)}
          </p>
        )}
        <div className="flex items-center gap-2">
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-surface-active text-text-tertiary capitalize">
            {memory.memory_type}
          </span>
          <span className="text-[11px] text-text-tertiary font-mono">
            {memory.filepath.split("/").pop()}
          </span>
        </div>
      </motion.div>
    </div>
  );
}
