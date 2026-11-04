import React, { useEffect, useState } from "react";
import { Cpu, HardDrive, Shield, Sliders, Database, Check, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import type { ChatStorageStatus } from "@/types";

export const SettingsPage: React.FC = () => {
  const [minimizeToTray, setMinimizeToTray] = useState(true);
  const [autoIndex, setAutoIndex] = useState(true);
  const [llmProvider, setLlmProvider] = useState("ollama");
  const [apiKey, setApiKey] = useState("");
  const [postgresUrl, setPostgresUrl] = useState("");
  const [storageStatus, setStorageStatus] = useState<ChatStorageStatus | null>(null);
  const [pgTestStatus, setPgTestStatus] = useState<{ text: string; error?: boolean } | null>(null);
  const [isTestingPg, setIsTestingPg] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    api.getChatStorageStatus().then((status) => {
      setStorageStatus(status);
      if (status.engine === "postgresql" && status.url) {
        setPostgresUrl(status.url);
      }
    }).catch(console.error);
  }, []);

  const handleTestPostgres = async () => {
    setIsTestingPg(true);
    setPgTestStatus(null);
    try {
      const res = await api.configureChatStorage(postgresUrl);
      if (res.success) {
        setPgTestStatus({ text: res.message, error: false });
        const updated = await api.getChatStorageStatus();
        setStorageStatus(updated);
      } else {
        setPgTestStatus({ text: res.message || res.error || "Connection failed", error: true });
      }
    } catch (err: any) {
      setPgTestStatus({ text: err?.message || "Failed to reach backend", error: true });
    } finally {
      setIsTestingPg(false);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (postgresUrl) {
      handleTestPostgres();
    }
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings & Privacy</h1>
        <p className="text-xs text-text-secondary">
          Configure local-first AI processing, background ingestion, and storage preferences
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* General Application */}
        <div className="p-6 rounded-xl border border-border bg-surface space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Sliders className="w-4 h-4 text-primary" />
            General & Desktop Behavior
          </div>

          <div className="flex items-center justify-between py-2 border-t border-border/50">
            <div>
              <p className="text-sm font-medium text-text-primary">Minimize to System Tray</p>
              <p className="text-xs text-text-secondary">
                Keep background file monitoring active when the main window is closed
              </p>
            </div>
            <input
              type="checkbox"
              checked={minimizeToTray}
              onChange={(e) => setMinimizeToTray(e.target.checked)}
              className="w-4 h-4 accent-primary rounded cursor-pointer"
            />
          </div>

          <div className="flex items-center justify-between py-2 border-t border-border/50">
            <div>
              <p className="text-sm font-medium text-text-primary">Auto-index Authorized Folders</p>
              <p className="text-xs text-text-secondary">
                Automatically detect and extract new files via filesystem watcher
              </p>
            </div>
            <input
              type="checkbox"
              checked={autoIndex}
              onChange={(e) => setAutoIndex(e.target.checked)}
              className="w-4 h-4 accent-primary rounded cursor-pointer"
            />
          </div>
        </div>

        {/* AI & Embeddings */}
        <div className="p-6 rounded-xl border border-border bg-surface space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Cpu className="w-4 h-4 text-primary" />
            AI & Processing Pipeline
          </div>

          <div className="space-y-2 border-t border-border/50 pt-3">
            <label className="block text-xs font-medium text-text-secondary">
              LLM Reasoning Engine
            </label>
            <select
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary"
            >
              <option value="ollama">Ollama Local Offline (Llama 3.2, Mistral, Phi-3 - 100% Offline)</option>
              <option value="local">Deterministic Template Synthesis (Lightweight Offline)</option>
              <option value="openai">OpenAI Compatible Endpoint</option>
              <option value="gemini">Google Gemini API</option>
            </select>
          </div>

          {llmProvider !== "local" && (
            <div className="space-y-2">
              <label className="block text-xs font-medium text-text-secondary">
                External Model API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary font-mono"
              />
            </div>
          )}

          <div className="py-2 border-t border-border/50 text-xs text-text-tertiary">
            Local Embedding Model: <span className="font-mono text-text-secondary">all-MiniLM-L6-v2</span> (384-dim, ONNX/PyTorch)
          </div>
        </div>

        {/* Privacy & Storage */}
        <div className="p-6 rounded-xl border border-border bg-surface space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Shield className="w-4 h-4 text-success" />
            Privacy & Local Storage
          </div>

          <div className="space-y-1 border-t border-border/50 pt-3 text-xs text-text-secondary">
            <p className="font-medium text-text-primary">Local-First Storage Guarantee</p>
            <p>
              ContextOS keeps your original files in place. Extracted embeddings, memories,
              and graphs are stored securely in SQLite on your device and are never sent
              to any third-party server without explicit consent.
            </p>
          </div>

          <div className="pt-2 flex items-center justify-between text-xs">
            <span className="text-text-tertiary flex items-center gap-1.5">
              <HardDrive className="w-4 h-4" />
              Location: %LOCALAPPDATA%\ContextOS
            </span>
          </div>
        </div>

        {/* PostgreSQL Persistent Chat Storage */}
        <div className="p-6 rounded-xl border border-border bg-surface space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Database className="w-4 h-4 text-primary" />
              PostgreSQL Database Configuration
            </div>
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                storageStatus?.engine === "postgresql"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                  : "bg-surface-active text-text-secondary border border-border"
              }`}
            >
              Active: {storageStatus?.engine === "postgresql" ? "PostgreSQL" : "SQLite Local"}
            </span>
          </div>

          <p className="text-xs text-text-secondary">
            ContextOS persists multi-session chat histories and conversational context memory to PostgreSQL.
            If left unconfigured or unreachable, ContextOS automatically falls back to local SQLite with zero downtime.
          </p>

          <div className="space-y-2 border-t border-border/50 pt-3">
            <label className="block text-xs font-medium text-text-secondary">
              PostgreSQL Connection URI
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={postgresUrl}
                onChange={(e) => setPostgresUrl(e.target.value)}
                placeholder="postgresql://postgres:password@localhost:5432/contextos"
                className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-xs font-mono text-text-primary focus:outline-none focus:border-primary"
              />
              <button
                type="button"
                onClick={handleTestPostgres}
                disabled={isTestingPg}
                className="px-4 py-2 bg-surface hover:bg-surface-hover border border-border rounded-lg text-xs text-text-secondary font-medium transition-colors shrink-0"
              >
                {isTestingPg ? "Connecting..." : "Test & Connect"}
              </button>
            </div>
          </div>

          {pgTestStatus && (
            <div
              className={`text-xs flex items-center gap-1.5 p-2.5 rounded-lg border ${
                pgTestStatus.error
                  ? "bg-red-500/10 border-red-500/30 text-red-400"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              }`}
            >
              {pgTestStatus.error ? (
                <AlertCircle className="w-4 h-4 shrink-0" />
              ) : (
                <Check className="w-4 h-4 shrink-0" />
              )}
              <span>{pgTestStatus.text}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-2">
          {savedSuccess && (
            <span className="text-xs text-success font-medium animate-fade-in">
              ✓ Preferences updated successfully
            </span>
          )}
          <div className="ml-auto">
            <button
              type="submit"
              className="px-5 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
            >
              Save Preferences
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default SettingsPage;
