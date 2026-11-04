import React, { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Calendar, Clock, Loader2, ChevronDown, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/app";
import TimelineItem from "@/components/TimelineItem";
import EmptyState from "@/components/EmptyState";
import type { Memory } from "@/types";

export const TimelinePage: React.FC = () => {
  const navigate = useNavigate();
  const { stats } = useAppStore();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 200;
  const [hasMore, setHasMore] = useState(true);

  const fetchTimeline = async (pageToFetch: number, append = false) => {
    if (append) {
      setIsLoadingMore(true);
    } else {
      setIsLoading(true);
    }

    try {
      const res = await api.listMemories({
        page: pageToFetch,
        per_page: pageSize,
      });
      const items: Memory[] = (res as any)?.items || res || [];
      const safeItems = Array.isArray(items) ? items : [];

      setMemories((prev) => {
        const combined = append ? [...prev, ...safeItems] : safeItems;
        // Deduplicate by ID
        const seen = new Set<string>();
        return combined.filter((item) => {
          if (seen.has(item.id)) return false;
          seen.add(item.id);
          return true;
        });
      });

      if (safeItems.length < pageSize) {
        setHasMore(false);
      } else {
        setHasMore(true);
      }
    } catch {
      if (!append) setMemories([]);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchTimeline(1, false);
  }, []);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchTimeline(nextPage, true);
  };

  // Group memories chronologically by date string
  const groupedMemories = useMemo(() => {
    const sorted = [...memories].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    const groups: { [dateKey: string]: Memory[] } = {};
    for (const mem of sorted) {
      const d = new Date(mem.created_at);
      const today = new Date();
      const yesterday = new Date();
      yesterday.setDate(today.getDate() - 1);

      let key: string;
      if (d.toDateString() === today.toDateString()) {
        key = "Today";
      } else if (d.toDateString() === yesterday.toDateString()) {
        key = "Yesterday";
      } else {
        key = d.toLocaleDateString("en-US", {
          weekday: "short",
          month: "short",
          day: "numeric",
          year: d.getFullYear() !== today.getFullYear() ? "numeric" : undefined,
        });
      }

      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(mem);
    }
    return groups;
  }, [memories]);

  const totalVaultCount = stats?.total_memories || memories.length;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text-primary">
            Temporal Memory Timeline
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            Chronological progression of captured ideas, documents, and concepts (
            <span className="font-mono text-text-primary font-medium">
              {memories.length}
            </span>{" "}
            loaded of{" "}
            <span className="font-mono text-text-primary font-medium">
              {totalVaultCount.toLocaleString()}
            </span>{" "}
            memories)
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-tertiary">
          <Clock className="w-3.5 h-3.5" />
          <span>Newest First</span>
        </div>
      </div>

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-2 text-text-tertiary text-xs">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading vault timeline...</span>
        </div>
      ) : memories.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="No timeline history"
          description="As you save files, notes, and screenshots, they will form an evolving timeline here."
        />
      ) : (
        <div className="space-y-8 pt-2">
          {Object.entries(groupedMemories).map(([dateLabel, groupItems]) => (
            <div key={dateLabel} className="space-y-3">
              {/* Sticky date header badge */}
              <div className="sticky top-2 z-10 flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full bg-surface border border-border text-[11px] font-semibold text-text-primary shadow-xs">
                  {dateLabel}
                </span>
                <span className="text-[10px] text-text-tertiary">
                  ({groupItems.length} {groupItems.length === 1 ? "entry" : "entries"})
                </span>
                <div className="flex-1 h-px bg-border" />
              </div>

              {/* Items for this date */}
              <div className="pt-1">
                {groupItems.map((mem, index) => (
                  <TimelineItem
                    key={mem.id}
                    memory={mem}
                    isLast={index === groupItems.length - 1}
                    onClick={(id) => navigate(`/memories/${id}`)}
                  />
                ))}
              </div>
            </div>
          ))}

          {/* Load More Button */}
          {hasMore && (
            <div className="pt-4 flex justify-center">
              <button
                onClick={handleLoadMore}
                disabled={isLoadingMore}
                className="px-4 py-2 bg-surface hover:bg-surface-hover border border-border text-text-primary text-xs font-medium rounded-lg flex items-center gap-2 transition-colors shadow-xs disabled:opacity-50"
              >
                {isLoadingMore ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Loading next 200 entries...</span>
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5" />
                    <span>
                      Load More Memories (
                      {Math.max(0, totalVaultCount - memories.length)} remaining)
                    </span>
                  </>
                )}
              </button>
            </div>
          )}

          {!hasMore && memories.length > 0 && (
            <div className="py-6 flex items-center justify-center gap-1.5 text-xs text-text-tertiary">
              <CheckCircle2 className="w-4 h-4 text-accent" />
              <span>All {memories.length} memories loaded chronologically</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TimelinePage;