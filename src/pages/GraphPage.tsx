import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  GitBranch,
  RefreshCw,
  X,
  Sparkles,
  FileText,
  FolderGit2,
  Cpu,
  Calendar,
  User,
  MessageSquare,
  Search,
  ExternalLink,
  Layers,
  ArrowRight,
  Clock,
} from "lucide-react";
import { api } from "@/lib/api";
import GraphVisualization from "@/components/GraphVisualization";
import { cn, getEntityTypeColor } from "@/lib/utils";
import type { GraphData } from "@/types";

function getNodeIcon(type: string) {
  const t = (type || "").toLowerCase();
  if (t === "document" || t === "webpage") return FileText;
  if (t === "project") return FolderGit2;
  if (t === "technology" || t === "tool") return Cpu;
  if (t === "person" || t === "author") return User;
  if (t === "date" || t === "event") return Calendar;
  return Sparkles;
}

export const GraphPage: React.FC = () => {
  const navigate = useNavigate();
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Selected node state for slide-over inspector
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeDetail, setNodeDetail] = useState<any | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  const loadGraph = async () => {
    setIsLoading(true);
    try {
      const data = await api.getGraphData();
      setGraphData(data);
    } catch {
      setGraphData({ nodes: [], edges: [] });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, []);

  // Fetch node detail when a node is clicked
  useEffect(() => {
    if (!selectedNodeId) {
      setNodeDetail(null);
      return;
    }

    let isMounted = true;
    setIsLoadingDetail(true);

    api
      .getNodeDetail(selectedNodeId)
      .then((detail) => {
        if (isMounted) setNodeDetail(detail);
      })
      .catch((err) => {
        console.error("Failed to load node detail:", err);
      })
      .finally(() => {
        if (isMounted) setIsLoadingDetail(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedNodeId]);

  const handleNodeClick = (nodeId: string) => {
    setSelectedNodeId(nodeId);
  };

  const handleAskAbout = (label: string) => {
    navigate(`/ask?q=${encodeURIComponent(`What do my memories tell me about ${label}?`)}`);
  };

  const handleSearchMemories = (label: string) => {
    navigate(`/memories?q=${encodeURIComponent(label)}`);
  };

  const Icon = nodeDetail ? getNodeIcon(nodeDetail.type) : Sparkles;
  const color = nodeDetail ? getEntityTypeColor(nodeDetail.type) : "#6366f1";

  return (
    <div className="flex flex-col h-full p-6 space-y-4 relative overflow-hidden">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-primary flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-primary" />
            Temporal Knowledge Graph
          </h1>
          <p className="text-xs text-text-secondary">
            Hover over nodes for quick inspection • Click any node to open its memories, relationships, and queries
          </p>
        </div>

        <button
          onClick={loadGraph}
          className="px-3 py-1.5 bg-surface hover:bg-surface-hover border border-border rounded-lg text-xs text-text-secondary flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-primary" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Main Canvas & Slide-over Container */}
      <div className="flex-1 border border-border rounded-2xl bg-surface/50 overflow-hidden relative shadow-inner flex">
        {/* Graph Canvas */}
        <div className="flex-1 h-full w-full">
          <GraphVisualization
            data={graphData}
            loading={isLoading}
            onNodeClick={handleNodeClick}
            className="w-full h-full"
          />
        </div>

        {/* Slide-over Node Detail Inspector */}
        {selectedNodeId && (
          <div className="absolute right-0 top-0 bottom-0 w-[420px] max-w-full bg-surface/95 backdrop-blur-xl border-l border-border/80 shadow-2xl z-30 flex flex-col animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-5 border-b border-border/80 flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 min-w-0">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-md mt-0.5"
                  style={{ backgroundColor: `${color}25`, color }}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <h2
                    className="text-base font-bold text-text-primary truncate"
                    title={nodeDetail?.label || "Node Details"}
                  >
                    {isLoadingDetail ? "Loading..." : nodeDetail?.label}
                  </h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: `${color}20`, color }}
                    >
                      {nodeDetail?.type || "Node"}
                    </span>
                    {nodeDetail?.mention_count !== undefined && (
                      <span className="text-xs text-text-tertiary">
                        {nodeDetail.mention_count} {nodeDetail.mention_count === 1 ? "reference" : "references"}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedNodeId(null)}
                className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors"
                title="Close Inspector"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {isLoadingDetail ? (
                <div className="flex flex-col items-center justify-center py-16 space-y-3">
                  <div className="w-7 h-7 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  <p className="text-xs text-text-secondary">Retrieving associative memory context...</p>
                </div>
              ) : nodeDetail ? (
                <>
                  {/* Action Buttons */}
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleAskAbout(nodeDetail.label)}
                      className="px-3 py-2.5 bg-primary/10 hover:bg-primary/20 border border-primary/30 rounded-xl text-xs font-semibold text-primary flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      Ask ContextOS
                    </button>
                    <button
                      onClick={() => handleSearchMemories(nodeDetail.label)}
                      className="px-3 py-2.5 bg-surface hover:bg-surface-hover border border-border rounded-xl text-xs font-semibold text-text-secondary flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                    >
                      <Search className="w-3.5 h-3.5" />
                      View in Memories
                    </button>
                  </div>

                  {/* Metadata Card */}
                  {(nodeDetail.file_type || nodeDetail.created_at || nodeDetail.first_seen) && (
                    <div className="bg-surface-hover/60 border border-border/60 rounded-xl p-3.5 space-y-2 text-xs">
                      {nodeDetail.file_type && (
                        <div className="flex justify-between items-center text-text-secondary">
                          <span className="text-text-tertiary">Source Type</span>
                          <span className="font-medium uppercase">{nodeDetail.file_type}</span>
                        </div>
                      )}
                      {(nodeDetail.created_at || nodeDetail.first_seen) && (
                        <div className="flex justify-between items-center text-text-secondary">
                          <span className="text-text-tertiary">First Indexed</span>
                          <span className="font-medium flex items-center gap-1">
                            <Clock className="w-3 h-3 text-text-tertiary" />
                            {new Date(nodeDetail.created_at || nodeDetail.first_seen).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                      {nodeDetail.original_path && (
                        <div className="pt-1 border-t border-border/40 text-[11px] text-text-tertiary truncate" title={nodeDetail.original_path}>
                          Path: {nodeDetail.original_path}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Connected Graph Nodes */}
                  {nodeDetail.connections && nodeDetail.connections.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-text-primary">
                        <Layers className="w-3.5 h-3.5 text-primary" />
                        Connected Associative Nodes ({nodeDetail.connections.length})
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {nodeDetail.connections.map((conn: any, idx: number) => {
                          const connColor = getEntityTypeColor(conn.type);
                          return (
                            <button
                              key={`${conn.id}-${idx}`}
                              onClick={() => setSelectedNodeId(conn.id)}
                              className="px-2.5 py-1.5 rounded-lg border bg-surface/80 hover:bg-surface-active text-xs flex items-center gap-1.5 transition-colors text-left"
                              style={{ borderColor: `${connColor}40` }}
                              title={`Jump to ${conn.label}`}
                            >
                              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: connColor }} />
                              <span className="text-text-primary font-medium truncate max-w-[140px]">{conn.label}</span>
                              <span className="text-[10px] text-text-tertiary">({conn.relationship})</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Associated Memories & Content Chunks */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs font-semibold text-text-primary">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-3.5 h-3.5 text-secondary" />
                        Memory Chunks & Quotes ({nodeDetail.memories?.length || 0})
                      </div>
                    </div>

                    {(!nodeDetail.memories || nodeDetail.memories.length === 0) ? (
                      <p className="text-xs text-text-tertiary italic py-2">No direct memory snippets recorded yet.</p>
                    ) : (
                      <div className="space-y-2.5">
                        {nodeDetail.memories.map((mem: any, idx: number) => (
                          <div
                            key={mem.id || idx}
                            className="bg-surface/80 hover:bg-surface border border-border/80 rounded-xl p-3 space-y-1.5 transition-colors"
                          >
                            <p className="text-xs text-text-primary leading-relaxed line-clamp-4">
                              {mem.content}
                            </p>
                            {mem.timestamp && (
                              <div className="flex justify-between items-center pt-1 border-t border-border/40 text-[10px] text-text-tertiary">
                                <span>Memory Chunk #{idx + 1}</span>
                                <span>{new Date(mem.timestamp).toLocaleString()}</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GraphPage;
