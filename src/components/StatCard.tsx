import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  delta?: string;
  deltaType?: "positive" | "negative" | "neutral";
  accentColor?: string;
  className?: string;
}

export default function StatCard({
  icon: Icon,
  label,
  value,
  delta,
  deltaType = "neutral",
  accentColor = "from-primary to-secondary",
  className,
}: StatCardProps) {
  const deltaColors = {
    positive: "text-success",
    negative: "text-danger",
    neutral: "text-text-tertiary",
  };

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface p-4 transition-colors",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider">
            {label}
          </p>
          <p className="text-2xl font-semibold text-text-primary tabular-nums tracking-tight">
            {typeof value === "number" ? value.toLocaleString() : value}
          </p>
          {delta && (
            <p className={cn("text-xs font-medium", deltaColors[deltaType])}>
              {delta}
            </p>
          )}
        </div>
        <div className="w-7 h-7 rounded-md bg-surface-active border border-border flex items-center justify-center">
          <Icon className="w-3.5 h-3.5 text-text-tertiary" />
        </div>
      </div>
    </div>
  );
}
