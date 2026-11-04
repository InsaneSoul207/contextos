import React from "react";
import { useAppStore } from "@/store/app";
import { Activity, CheckCircle, Database } from "lucide-react";

export const StatusBar: React.FC = () => {
  const { systemStatus, stats } = useAppStore();

  return (
    <div className="h-7 border-t border-border bg-[#f5f2eb] px-4 flex items-center justify-between text-[11px] text-text-tertiary select-none">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              systemStatus.indexing
                ? "bg-warning animate-pulse"
                : "bg-success"
            }`}
          />
          <span className="text-text-secondary">
            {systemStatus.indexing ? "Indexing..." : "Idle"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <span>{stats?.total_memories ?? 0} memories</span>
        <span>·</span>
        <span>Local v0.1.0</span>
      </div>
    </div>
  );
};

export default StatusBar;
