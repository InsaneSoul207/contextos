import { useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import {
  User,
  Brain,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { cn, formatRelativeDate } from "@/lib/utils";
import type { ChatMessage as ChatMessageType, SearchResult } from "@/types";

interface ChatMessageProps {
  message: ChatMessageType;
  isTyping?: boolean;
}

export default function ChatMessage({ message, isTyping }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === "user";

  if (isTyping) {
    return (
      <div className="flex gap-2.5 items-start">
        <div className="w-6 h-6 rounded-md bg-surface-active border border-border flex items-center justify-center flex-shrink-0 text-[10px] font-semibold text-text-secondary">
          C
        </div>
        <div className="bg-surface/60 border border-border/80 rounded-xl px-3.5 py-2.5">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-text-secondary animate-pulse" />
            <span className="text-xs text-text-secondary">Thinking...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className={cn(
        "flex gap-2.5 items-start",
        isUser && "flex-row-reverse"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 text-[10px] font-medium border border-border",
          isUser
            ? "bg-surface-active text-text-secondary"
            : "bg-surface text-text-primary"
        )}
      >
        {isUser ? "You" : "C"}
      </div>

      {/* Content */}
      <div
        className={cn(
          "rounded-xl px-4 py-2.5",
          isUser
            ? "max-w-[75%] bg-[#ebe4d8] border border-[#ded5c6] text-text-primary rounded-tr-xs shadow-xs"
            : "max-w-[85%] bg-surface border border-border text-text-primary rounded-tl-xs shadow-xs"
        )}
      >
        {isUser ? (
          <p className="text-xs sm:text-sm leading-relaxed">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none text-text-primary">
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <p className="text-xs sm:text-sm text-text-primary leading-relaxed mb-2 last:mb-0">
                    {children}
                  </p>
                ),
                code: ({ children }) => (
                  <code className="px-1.5 py-0.5 rounded bg-surface-hover text-text-primary font-mono text-xs border border-border">
                    {children}
                  </code>
                ),
                pre: ({ children }) => (
                  <pre className="bg-surface-hover border border-border rounded-lg p-3 my-2 overflow-x-auto text-text-primary text-xs">
                    {children}
                  </pre>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc list-inside space-y-1 text-xs sm:text-sm text-text-primary">
                    {children}
                  </ul>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold text-text-primary">
                    {children}
                  </strong>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Source Citations */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1.5 text-xs text-text-tertiary hover:text-text-secondary transition-colors"
            >
              {showSources ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
              {message.sources.length} source
              {message.sources.length !== 1 ? "s" : ""}
            </button>
            {showSources && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="mt-2 space-y-1.5"
              >
                {message.sources.map((result: any, i: number) => {
                  const title =
                    result.memory?.title ||
                    result.memory?.filepath ||
                    result.document_filename ||
                    result.source_name ||
                    `Source #${i + 1}`;
                  const score =
                    typeof result.score === "number"
                      ? Math.round(result.score * 100)
                      : null;
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-surface-hover text-xs cursor-pointer hover:bg-surface-active transition-colors"
                    >
                      <ExternalLink className="w-3 h-3 text-text-tertiary flex-shrink-0" />
                      <span className="text-text-secondary truncate">
                        {title}
                      </span>
                      {score !== null && (
                        <span className="text-text-tertiary ml-auto flex-shrink-0 font-mono">
                          {score}%
                        </span>
                      )}
                    </div>
                  );
                })}
              </motion.div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <p className="text-[10px] mt-2 text-text-tertiary">
          {formatRelativeDate(message.timestamp)}
        </p>
      </div>
    </motion.div>
  );
}
