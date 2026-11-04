import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import {
  format,
  formatDistanceToNow,
  isToday,
  isYesterday,
  isThisWeek,
  isThisMonth,
  isThisYear,
} from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string, fmt: string = "PPp"): string {
  try {
    return format(new Date(dateStr), fmt);
  } catch {
    return dateStr;
  }
}

export function formatRelativeDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return dateStr;
  }
}

export function getDateGroupLabel(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    if (isToday(date)) return "Today";
    if (isYesterday(date)) return "Yesterday";
    if (isThisWeek(date)) return "This Week";
    if (isThisMonth(date)) return "This Month";
    if (isThisYear(date)) return format(date, "MMMM");
    return format(date, "MMMM yyyy");
  } catch {
    return "Unknown";
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function truncateText(text: string, maxLength: number = 150): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trim() + "…";
}

export function getFileTypeIcon(
  fileType?: string
): "FileText" | "Image" | "Code" | "FileVideo" | "FileAudio" | "Globe" | "Camera" | "File" {
  if (!fileType) return "FileText";
  const type = String(fileType).toLowerCase();
  if (["jpg", "jpeg", "png", "gif", "svg", "webp", "bmp"].includes(type))
    return "Image";
  if (["mp4", "mov", "avi", "mkv", "webm"].includes(type)) return "FileVideo";
  if (["mp3", "wav", "ogg", "flac", "aac"].includes(type)) return "FileAudio";
  if (
    ["js", "ts", "py", "rs", "go", "java", "cpp", "c", "h", "css", "html", "json", "yaml", "toml", "xml"].includes(type)
  )
    return "Code";
  if (["txt", "md", "pdf", "doc", "docx", "rtf"].includes(type))
    return "FileText";
  if (["html", "htm", "url", "webpage"].includes(type)) return "Globe";
  if (type === "screenshot") return "Camera";
  return "File";
}

export function getFileTypeColor(fileType?: string): string {
  if (!fileType) return "text-text-secondary";
  const icon = getFileTypeIcon(fileType);
  switch (icon) {
    case "Image":
    case "Camera":
      return "text-green-400";
    case "FileVideo":
      return "text-purple-400";
    case "FileAudio":
      return "text-pink-400";
    case "Code":
      return "text-cyan-400";
    case "FileText":
      return "text-blue-400";
    case "Globe":
      return "text-orange-400";
    default:
      return "text-text-secondary";
  }
}

export function getEntityTypeColor(entityType?: string): string {
  if (!entityType) return "#64748b";
  switch (entityType.toLowerCase()) {
    case "person":
      return "#3b82f6";
    case "project":
      return "#8b5cf6";
    case "topic":
      return "#06b6d4";
    case "document":
      return "#22c55e";
    case "event":
      return "#f59e0b";
    case "concept":
      return "#ec4899";
    case "organization":
      return "#f97316";
    case "location":
      return "#14b8a6";
    case "technology":
    case "tech":
      return "#6366f1";
    case "date":
      return "#eab308";
    case "webpage":
    case "url":
      return "#f97316";
    default:
      return "#818cf8";
  }
}
