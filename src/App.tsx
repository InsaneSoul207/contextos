import React, { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { Plus, Download, Sparkles } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import SearchBar from "@/components/SearchBar";
import StatusBar from "@/components/StatusBar";
import QuickCaptureModal from "@/components/QuickCaptureModal";
import SpotlightModal from "@/components/SpotlightModal";
import Dashboard from "@/pages/Dashboard";
import AskPage from "@/pages/AskPage";
import MemoriesPage from "@/pages/MemoriesPage";
import MemoryDetailPage from "@/pages/MemoryDetailPage";
import TimelinePage from "@/pages/TimelinePage";
import GraphPage from "@/pages/GraphPage";
import SourcesPage from "@/pages/SourcesPage";
import CollectionsPage from "@/pages/CollectionsPage";
import SettingsPage from "@/pages/SettingsPage";
import { useAppStore } from "@/store/app";
import { api } from "@/lib/api";

export const App: React.FC = () => {
  const { fetchStats } = useAppStore();
  const [isQuickCaptureOpen, setIsQuickCaptureOpen] = useState(false);
  const [isSpotlightOpen, setIsSpotlightOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  // Global macOS Spotlight Shortcuts: Ctrl+K, Ctrl+Space, Alt+Space, Alt+K
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      const isKeyK = e.key === "k" || e.key === "K" || e.code === "KeyK";
      const isSpace = e.code === "Space" || e.key === " ";

      const isCtrlK = (e.ctrlKey || e.metaKey) && isKeyK;
      const isCtrlSpace = (e.ctrlKey || e.metaKey) && isSpace;
      const isAltSpace = e.altKey && isSpace;
      const isAltK = e.altKey && isKeyK;

      if (isCtrlK || isCtrlSpace || isAltSpace || isAltK) {
        e.preventDefault();
        e.stopPropagation();
        setIsSpotlightOpen((prev) => !prev);
      }
    };
    const handleOpenSpotlight = () => setIsSpotlightOpen(true);

    window.addEventListener("keydown", handleGlobalKeyDown, true);
    window.addEventListener("open-spotlight", handleOpenSpotlight);
    return () => {
      window.removeEventListener("keydown", handleGlobalKeyDown, true);
      window.removeEventListener("open-spotlight", handleOpenSpotlight);
    };
  }, []);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const data = await api.exportAll();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `contextos_vault_export_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export vault:", err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-text-primary font-sans antialiased">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Global Top Search Bar & Action Controls */}
        <header className="h-12 border-b border-border px-4 flex items-center justify-between bg-[#f5f2eb]/90 backdrop-blur-md flex-shrink-0 z-20 gap-3">
          <div className="w-full max-w-lg">
            <SearchBar />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsQuickCaptureOpen(true)}
              className="px-2.5 py-1 bg-text-primary hover:opacity-90 text-surface rounded-md text-xs font-medium flex items-center gap-1.5 transition-opacity"
              title="Capture notes or paste text from clipboard"
            >
              <Plus className="w-3.5 h-3.5" />
              Capture
            </button>

            <button
              onClick={handleExport}
              disabled={isExporting}
              className="px-2.5 py-1 bg-surface hover:bg-surface-hover border border-border text-text-secondary hover:text-text-primary rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors"
              title="Export vault"
            >
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
          </div>
        </header>

        {/* Dynamic Route Content */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/ask" element={<AskPage />} />
            <Route path="/memories" element={<MemoriesPage />} />
            <Route path="/memories/:id" element={<MemoryDetailPage />} />
            <Route path="/timeline" element={<TimelinePage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/sources" element={<SourcesPage />} />
            <Route path="/collections" element={<CollectionsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>

        {/* System Status Bar */}
        <StatusBar />
      </div>

      {/* Quick Capture Modal */}
      <QuickCaptureModal
        isOpen={isQuickCaptureOpen}
        onClose={() => setIsQuickCaptureOpen(false)}
        onSuccess={() => fetchStats()}
      />

      {/* macOS Spotlight Quick-Recall Modal (Alt+Space / Ctrl+K) */}
      <SpotlightModal
        isOpen={isSpotlightOpen}
        onClose={() => setIsSpotlightOpen(false)}
      />
    </div>
  );
};

export default App;
