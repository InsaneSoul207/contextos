import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  X,
  Search,
  FileText,
  Sparkles,
  FolderGit2,
  Cpu,
  Calendar,
  User,
  ArrowRight,
  Info,
} from "lucide-react";
import { cn, getEntityTypeColor } from "@/lib/utils";
import type { GraphData, GraphNode, EntityType } from "@/types";

// Helper to pick contextual icons
function getNodeIcon(type: string) {
  const t = (type || "").toLowerCase();
  if (t === "document" || t === "webpage") return FileText;
  if (t === "project") return FolderGit2;
  if (t === "technology" || t === "tool") return Cpu;
  if (t === "person" || t === "author") return User;
  if (t === "date" || t === "event") return Calendar;
  return Sparkles; // Concept, Topic, default
}

// ===== Custom Node Component =====
function EntityNode({ data }: NodeProps) {
  const [isHovered, setIsHovered] = useState(false);
  const nodeData = data as { label: string; entityType: string; size?: number };
  const color = getEntityTypeColor(nodeData.entityType);
  const Icon = getNodeIcon(nodeData.entityType);
  const mentions = typeof nodeData.size === "number" ? nodeData.size : 1;

  return (
    <div
      className="relative select-none"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-2 !h-2" />

      {/* Main Node Card */}
      <div
        className={cn(
          "flex items-center gap-2.5 px-3 py-2 rounded-xl border backdrop-blur-md shadow-lg cursor-pointer transition-all duration-200",
          "hover:scale-105 hover:shadow-2xl z-20",
          isHovered ? "ring-2 ring-primary/80 shadow-primary/25" : ""
        )}
        style={{
          backgroundColor: "#13131dee",
          borderColor: isHovered ? color : `${color}60`,
          minWidth: 130,
          maxWidth: 240,
        }}
      >
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 shadow-sm"
          style={{ backgroundColor: `${color}25`, color }}
        >
          <Icon className="w-4 h-4" />
        </div>

        <div className="flex flex-col min-w-0 pr-1">
          <span className="text-xs font-semibold text-text-primary truncate" title={nodeData.label}>
            {nodeData.label}
          </span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span
              className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
              style={{ backgroundColor: `${color}20`, color }}
            >
              {nodeData.entityType}
            </span>
            <span className="text-[10px] text-text-tertiary">
              {mentions} {mentions === 1 ? "ref" : "refs"}
            </span>
          </div>
        </div>
      </div>

      {/* Floating Hover Info Tooltip */}
      {isHovered && (
        <div className="absolute left-1/2 -top-16 -translate-x-1/2 z-50 pointer-events-none whitespace-nowrap animate-in fade-in zoom-in-95 duration-150">
          <div className="bg-surface/95 border border-border/80 px-3 py-2 rounded-xl shadow-2xl backdrop-blur-md flex flex-col gap-0.5 text-center min-w-[160px]">
            <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-text-primary">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
              <span className="truncate max-w-[200px]">{nodeData.label}</span>
            </div>
            <div className="text-[11px] text-text-secondary flex items-center justify-center gap-2">
              <span className="capitalize">{nodeData.entityType}</span>
              <span>•</span>
              <span className="text-primary font-medium flex items-center gap-1">
                Click to inspect <ArrowRight className="w-3 h-3 inline" />
              </span>
            </div>
          </div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

// ===== Entity Type Filters =====
const entityTypes: string[] = [
  "person",
  "project",
  "topic",
  "document",
  "event",
  "concept",
  "technology",
  "date",
  "webpage",
];

// ===== Main Component =====
interface GraphVisualizationProps {
  data: GraphData | null;
  loading?: boolean;
  onNodeClick?: (nodeId: string) => void;
  className?: string;
}

export default function GraphVisualization({
  data,
  loading,
  onNodeClick,
  className,
}: GraphVisualizationProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(entityTypes)
  );
  const [showFilters, setShowFilters] = useState(false);

  const toggleFilter = (type: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const filteredData = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };

    const filteredNodes = data.nodes.filter((n) => {
      const typeLower = (n.type || "concept").toLowerCase();
      const matchesFilter =
        activeFilters.has(typeLower) || activeFilters.size === 0;
      const matchesSearch =
        !searchTerm || n.label.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesFilter && matchesSearch;
    });

    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = data.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    return { nodes: filteredNodes, edges: filteredEdges };
  }, [data, activeFilters, searchTerm]);

  const rfNodes: Node[] = useMemo(() => {
    const total = filteredData.nodes.length;
    return filteredData.nodes.map((node: GraphNode, i: number) => {
      const angle = (i / Math.max(1, total)) * Math.PI * 2;
      const radius = total > 1 ? 220 + Math.min(total * 28, 280) : 0;
      return {
        id: node.id,
        type: "entity",
        position: {
          x: 450 + Math.cos(angle) * radius,
          y: 320 + Math.sin(angle) * radius,
        },
        data: {
          label: node.label,
          entityType: node.type,
          size: node.size || (node as any).mention_count || 2,
        },
      };
    });
  }, [filteredData.nodes]);

  const rfEdges: Edge[] = useMemo(
    () =>
      filteredData.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        style: { stroke: "#6366f1", strokeWidth: Math.max(1.5, edge.weight || 1.5) },
        labelStyle: {
          fill: "#94a3b8",
          fontSize: 10,
          fontFamily: "Inter",
        },
        labelBgStyle: {
          fill: "#12121a",
          fillOpacity: 0.85,
        },
        labelBgPadding: [4, 2] as [number, number],
        type: "default",
      })),
    [filteredData.edges]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(rfNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(rfEdges);

  // Sync when rfNodes/rfEdges change
  useEffect(() => {
    setNodes(rfNodes);
  }, [rfNodes, setNodes]);

  useEffect(() => {
    setEdges(rfEdges);
  }, [rfEdges, setEdges]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  if (loading) {
    return (
      <div className={cn("flex items-center justify-center bg-background", className)}>
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-text-secondary">Loading graph...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("relative bg-background", className)}>
      {/* Filter Bar */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
        <div className="flex items-center gap-2 bg-surface/90 backdrop-blur-sm border border-border rounded-lg px-3 py-2">
          <Search className="w-3.5 h-3.5 text-text-tertiary" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search graph..."
            className="bg-transparent border-none outline-none text-xs text-text-primary placeholder:text-text-tertiary w-32"
          />
          {searchTerm && (
            <button onClick={() => setSearchTerm("")}>
              <X className="w-3 h-3 text-text-tertiary hover:text-text-primary" />
            </button>
          )}
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            "px-3 py-2 text-xs rounded-lg border transition-colors",
            showFilters
              ? "bg-primary-muted text-primary border-primary/30"
              : "bg-surface/90 text-text-secondary border-border hover:text-text-primary"
          )}
        >
          Filters
        </button>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="absolute top-14 left-4 z-10 bg-surface/95 backdrop-blur-sm border border-border rounded-lg p-3 space-y-2">
          {entityTypes.map((type) => (
            <label
              key={type}
              className="flex items-center gap-2 cursor-pointer text-xs"
            >
              <input
                type="checkbox"
                checked={activeFilters.has(type)}
                onChange={() => toggleFilter(type)}
                className="rounded border-border bg-surface-active text-primary focus:ring-primary focus:ring-offset-0"
              />
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: getEntityTypeColor(type) }}
              />
              <span className="capitalize text-text-secondary">{type}</span>
            </label>
          ))}
        </div>
      )}

      {/* Node Count */}
      <div className="absolute top-4 right-4 z-10 bg-surface/90 backdrop-blur-sm border border-border rounded-lg px-3 py-2">
        <span className="text-xs text-text-tertiary">
          {filteredData.nodes.length} nodes · {filteredData.edges.length} edges
        </span>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1a1a25" />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const nd = node.data as { entityType: EntityType };
            return getEntityTypeColor(nd.entityType);
          }}
          maskColor="rgba(10, 10, 15, 0.7)"
        />
      </ReactFlow>
    </div>
  );
}
