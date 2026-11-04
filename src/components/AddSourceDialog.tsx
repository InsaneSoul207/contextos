import React, { useState } from "react";
import { Folder, X } from "lucide-react";
import { api } from "@/lib/api";
import type { SourceType } from "@/types";

interface AddSourceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSourceAdded: () => void;
}

export const AddSourceDialog: React.FC<AddSourceDialogProps> = ({
  isOpen,
  onClose,
  onSourceAdded,
}) => {
  const [displayName, setDisplayName] = useState("");
  const [path, setPath] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("documents");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleBrowse = async () => {
    try {
      // Check if Tauri dialog plugin is available
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        directory: true,
        multiple: false,
        title: "Select Monitored Folder",
      });
      if (selected && typeof selected === "string") {
        setPath(selected);
        if (!displayName) {
          const parts = selected.split(/[\\/]/);
          setDisplayName(parts[parts.length - 1] || "Monitored Folder");
        }
      }
    } catch {
      // Fallback for browser mode
      const manual = prompt("Enter full folder path to monitor:");
      if (manual) {
        setPath(manual);
        if (!displayName) {
          const parts = manual.split(/[\\/]/);
          setDisplayName(parts[parts.length - 1] || "Monitored Folder");
        }
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!path.trim()) {
      setError("Folder path is required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await api.createSource({
        display_name: displayName.trim() || path.split(/[\\/]/).pop() || "Folder",
        path: path.trim(),
        source_type: sourceType,
      });
      onSourceAdded();
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to add source folder.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md bg-surface border border-border rounded-xl shadow-2xl p-6 relative animate-in fade-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-text-tertiary hover:text-text-primary transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h2 className="text-lg font-semibold text-text-primary mb-1">
          Add Monitored Folder
        </h2>
        <p className="text-xs text-text-secondary mb-5">
          ContextOS will continuously track, ingest, and connect files saved here.
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/30 text-xs text-danger">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Folder Path
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="C:\Users\...\Documents\Research"
                className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary placeholder:text-text-tertiary font-mono"
              />
              <button
                type="button"
                onClick={handleBrowse}
                className="px-3 py-2 bg-surface-hover hover:bg-surface-active border border-border rounded-lg text-sm text-text-secondary flex items-center gap-1.5 transition-colors"
              >
                <Folder className="w-4 h-4" />
                Browse
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Display Name
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. AI Research Papers"
              className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary placeholder:text-text-tertiary"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Source Category
            </label>
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value as SourceType)}
              className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary"
            >
              <option value="documents">Documents</option>
              <option value="screenshots">Screenshots</option>
              <option value="research">Research</option>
              <option value="projects">Projects</option>
              <option value="downloads">Downloads</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary-hover disabled:opacity-50 rounded-lg transition-colors"
            >
              {isSubmitting ? "Connecting..." : "Authorise & Monitor"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddSourceDialog;
