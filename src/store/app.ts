import { create } from "zustand";
import type { Stats } from "@/types";
import api from "@/lib/api";

interface SystemStatus {
  indexing: boolean;
  connected_sources: number;
  pending_jobs: number;
  last_sync: string | null;
}

interface AppState {
  sidebarCollapsed: boolean;
  searchQuery: string;
  systemStatus: SystemStatus;
  stats: Stats | null;
  statsLoading: boolean;

  // Actions
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setSearchQuery: (query: string) => void;
  updateStatus: (status: Partial<SystemStatus>) => void;
  updateStats: (stats: Stats) => void;
  fetchStats: () => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  searchQuery: "",
  systemStatus: {
    indexing: false,
    connected_sources: 0,
    pending_jobs: 0,
    last_sync: null,
  },
  stats: null,
  statsLoading: false,

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  setSearchQuery: (query) => set({ searchQuery: query }),

  updateStatus: (status) =>
    set((state) => ({
      systemStatus: { ...state.systemStatus, ...status },
    })),

  updateStats: (stats) => set({ stats }),

  fetchStats: async () => {
    set({ statsLoading: true });
    try {
      const stats = await api.getStats();
      set({
        stats,
        statsLoading: false,
        systemStatus: {
          indexing: stats.processing_queue_size > 0,
          connected_sources: stats.total_sources,
          pending_jobs: stats.processing_queue_size,
          last_sync: stats.last_activity,
        },
      });
    } catch {
      set({ statsLoading: false });
    }
  },
}));
