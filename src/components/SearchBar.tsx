import { useRef } from "react";
import { Search, Command } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  large?: boolean;
  className?: string;
}

export default function SearchBar({
  large = false,
  className,
}: SearchBarProps) {
  const handleClick = () => {
    window.dispatchEvent(new CustomEvent("open-spotlight"));
  };

  return (
    <div
      onClick={handleClick}
      className={cn("relative cursor-pointer select-none", className)}
    >
      <motion.div
        className={cn(
          "relative flex items-center rounded-lg transition-colors",
          "bg-surface border border-border hover:border-border-hover",
          large ? "px-4 py-3" : "px-3 py-2"
        )}
      >
        <Search
          className={cn(
            "flex-shrink-0 text-text-tertiary transition-colors",
            large ? "w-5 h-5" : "w-4 h-4"
          )}
        />
        <span
          className={cn(
            "flex-1 text-text-tertiary ml-3 truncate",
            large ? "text-lg" : "text-sm"
          )}
        >
          Spotlight Recall (Ctrl + K or Ctrl + Space)...
        </span>

        <div className="flex items-center gap-1.5 text-text-tertiary flex-shrink-0">
          <kbd className="flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface-hover border border-border text-[10px] font-mono">
            <Command className="w-3 h-3" />K
          </kbd>
        </div>
      </motion.div>
    </div>
  );
}
