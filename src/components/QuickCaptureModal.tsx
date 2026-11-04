import React, { useEffect, useRef, useState } from "react";
import { Plus, X, Clipboard, Check, Sparkles, Image as ImageIcon, Camera, UploadCloud } from "lucide-react";
import { api } from "@/lib/api";

interface QuickCaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const QuickCaptureModal: React.FC<QuickCaptureModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  const [screenshotPreview, setScreenshotPreview] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copiedFromClipboard, setCopiedFromClipboard] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clear preview URL on unmount or file change
  useEffect(() => {
    return () => {
      if (screenshotPreview) URL.revokeObjectURL(screenshotPreview);
    };
  }, [screenshotPreview]);

  // Handle global paste for images/screenshots (e.g. from Snipping Tool / Win+Shift+S)
  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith("image/")) {
        const file = items[i].getAsFile();
        if (file) {
          e.preventDefault();
          handleSelectImage(file);
          return;
        }
      }
    }
  };

  const handleSelectImage = (file: File) => {
    setScreenshotFile(file);
    const url = URL.createObjectURL(file);
    setScreenshotPreview(url);
    if (!title) {
      setTitle(`Screenshot ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleSelectImage(file);
    }
  };

  const handlePasteClipboardText = async () => {
    try {
      // Check for image in clipboard first
      if (navigator.clipboard.read) {
        try {
          const items = await navigator.clipboard.read();
          for (const item of items) {
            const imageType = item.types.find((t) => t.startsWith("image/"));
            if (imageType) {
              const blob = await item.getType(imageType);
              const file = new File([blob], `screenshot_${Date.now()}.png`, { type: imageType });
              handleSelectImage(file);
              setCopiedFromClipboard(true);
              setTimeout(() => setCopiedFromClipboard(false), 2000);
              return;
            }
          }
        } catch {
          // Fall back to text
        }
      }

      const text = await navigator.clipboard.readText();
      if (text) {
        setContent((prev) => (prev ? `${prev}\n\n${text}` : text));
        setCopiedFromClipboard(true);
        setTimeout(() => setCopiedFromClipboard(false), 2000);
      }
    } catch {
      // Clipboard permissions denied
    }
  };

  const handleRemoveScreenshot = () => {
    if (screenshotPreview) URL.revokeObjectURL(screenshotPreview);
    setScreenshotFile(null);
    setScreenshotPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!content.trim() && !screenshotFile) || isSubmitting) return;

    setIsSubmitting(true);
    try {
      if (screenshotFile) {
        // Upload screenshot for Windows OCR & semantic vector embedding
        await api.uploadDocument(screenshotFile);
        // If user also entered additional notes, capture that as well
        if (content.trim()) {
          await api.quickCapture({
            content: `Notes on screenshot "${screenshotFile.name}":\n${content.trim()}`,
            title: title.trim() || undefined,
          });
        }
      } else {
        await api.quickCapture({
          content: content.trim(),
          title: title.trim() || undefined,
        });
      }

      handleRemoveScreenshot();
      setContent("");
      setTitle("");
      onSuccess?.();
      onClose();
    } catch (err) {
      console.error("Quick capture failed:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      onPaste={handlePaste}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150"
    >
      <div className="bg-surface border border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/20 text-primary flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-text-primary">Quick Capture Memory</h2>
              <p className="text-[11px] text-text-secondary">
                Paste screenshots (Ctrl+V), notes, or clipboard straight into ContextOS
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-hover"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-3.5">
          <div>
            <label className="block text-[11px] font-semibold text-text-tertiary mb-1">
              Title (Optional)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. System Design Diagram, Error Trace, Meeting Notes..."
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-text-primary placeholder:text-text-tertiary outline-none focus:border-primary"
            />
          </div>

          {/* Screenshot Preview or Dropzone */}
          {screenshotPreview ? (
            <div className="relative rounded-xl border border-border/80 overflow-hidden bg-background p-2 space-y-2">
              <div className="flex items-center justify-between text-xs text-text-secondary pb-1">
                <span className="flex items-center gap-1.5 font-medium text-[11px]">
                  <ImageIcon className="w-3.5 h-3.5 text-primary" />
                  {screenshotFile?.name || "Screenshot attached"}
                </span>
                <button
                  type="button"
                  onClick={handleRemoveScreenshot}
                  className="text-text-tertiary hover:text-red-400 text-[11px] flex items-center gap-1"
                >
                  <X className="w-3 h-3" />
                  Remove
                </button>
              </div>
              <div className="max-h-48 overflow-hidden rounded-lg bg-black/40 flex items-center justify-center">
                <img
                  src={screenshotPreview}
                  alt="Screenshot preview"
                  className="max-h-48 w-auto object-contain rounded-md"
                />
              </div>
              <p className="text-[10px] text-emerald-400 flex items-center gap-1">
                <Check className="w-3 h-3" />
                Windows native OCR will extract all visible text & code from this screenshot.
              </p>
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border border-dashed border-border hover:border-primary/50 bg-background/50 hover:bg-surface-hover/50 rounded-xl p-3 text-center cursor-pointer transition-colors space-y-1"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleFileInputChange}
                className="hidden"
              />
              <div className="flex items-center justify-center gap-2 text-xs text-text-secondary">
                <Camera className="w-4 h-4 text-primary" />
                <span className="font-medium">Paste screenshot (Ctrl+V) or browse image</span>
              </div>
              <p className="text-[10px] text-text-tertiary">
                Supports PNG, JPG, WebP. ContextOS extracts code, text, and architecture diagrams automatically.
              </p>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-[11px] font-semibold text-text-tertiary">
                {screenshotFile ? "Additional Notes / Context (Optional)" : "Memory Content *"}
              </label>
              <button
                type="button"
                onClick={handlePasteClipboardText}
                className="text-[11px] text-primary hover:underline flex items-center gap-1"
              >
                {copiedFromClipboard ? <Check className="w-3 h-3" /> : <Clipboard className="w-3 h-3" />}
                {copiedFromClipboard ? "Pasted!" : "Paste from Clipboard"}
              </button>
            </div>
            <textarea
              rows={screenshotPreview ? 3 : 4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={
                screenshotFile
                  ? "Add any extra thoughts, tags, or context about this screenshot..."
                  : "Type notes or paste code, articles, or thoughts..."
              }
              required={!screenshotFile}
              className="w-full bg-background border border-border rounded-xl p-3 text-xs text-text-primary placeholder:text-text-tertiary outline-none focus:border-primary resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/80">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:bg-surface-hover"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={(!content.trim() && !screenshotFile) || isSubmitting}
              className="px-4 py-1.5 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-md transition-colors"
            >
              {isSubmitting ? (
                <>OCR Scanning & Indexing...</>
              ) : (
                <>
                  <Plus className="w-3.5 h-3.5" />
                  Save to ContextOS
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default QuickCaptureModal;
