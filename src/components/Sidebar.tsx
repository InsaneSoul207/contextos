import { NavLink, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  MessageSquare,
  Brain,
  Clock,
  GitBranch,
  FolderOpen,
  Library,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/app";

const navItems = [
  { path: "/", label: "Home", icon: LayoutDashboard },
  { path: "/ask", label: "Ask ContextOS", icon: MessageSquare },
  { path: "/memories", label: "All Memories", icon: Brain },
  { path: "/timeline", label: "Timeline", icon: Clock },
  { path: "/graph", label: "Knowledge Graph", icon: GitBranch },
  { path: "/sources", label: "Sources", icon: FolderOpen },
  { path: "/collections", label: "Collections", icon: Library },
];

const bottomNavItems = [
  { path: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar, systemStatus } = useAppStore();

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarCollapsed ? 68 : 240 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="h-screen flex flex-col bg-[#f5f2eb] border-r border-border relative flex-shrink-0"
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-border flex-shrink-0">
        <div className="w-6 h-6 rounded-md bg-surface border border-border flex items-center justify-center text-xs font-semibold text-text-primary flex-shrink-0 shadow-xs">
          C
        </div>
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "auto" }}
              exit={{ opacity: 0, width: 0 }}
              className="text-sm font-semibold tracking-tight text-text-primary whitespace-nowrap overflow-hidden"
            >
              ContextOS
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive =
            item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors group relative",
                isActive
                  ? "bg-surface text-text-primary font-medium border border-border shadow-xs"
                  : "text-text-secondary hover:text-text-primary hover:bg-[#ede7da]"
              )}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <item.icon
                className={cn(
                  "w-4 h-4 flex-shrink-0 transition-colors",
                  isActive ? "text-text-primary" : "text-text-tertiary group-hover:text-text-secondary"
                )}
              />
              <AnimatePresence>
                {!sidebarCollapsed && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="whitespace-nowrap overflow-hidden"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </NavLink>
          );
        })}
      </nav>

      {/* Divider */}
      <div className="mx-3 border-t border-border" />

      {/* Bottom Nav */}
      <div className="py-2 px-2 space-y-1">
        {bottomNavItems.map((item) => {
          const isActive = location.pathname.startsWith(item.path);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors",
                isActive
                  ? "bg-surface text-text-primary font-medium border border-border shadow-xs"
                  : "text-text-secondary hover:text-text-primary hover:bg-[#ede7da]"
              )}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <item.icon
                className={cn(
                  "w-4 h-4 flex-shrink-0",
                  isActive ? "text-text-primary" : "text-text-tertiary"
                )}
              />
              <AnimatePresence>
                {!sidebarCollapsed && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="whitespace-nowrap overflow-hidden"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </NavLink>
          );
        })}
      </div>

      {/* System Status */}
      <div className="mx-3 border-t border-border" />
      <div className="px-3.5 py-3 flex-shrink-0">
        <div
          className={cn(
            "flex items-center gap-2 text-xs",
            sidebarCollapsed ? "justify-center" : ""
          )}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-success flex-shrink-0" />
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[11px] text-text-tertiary truncate"
              >
                {systemStatus.connected_sources} sources active
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Collapse Button */}
      <button
        onClick={toggleSidebar}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-surface border border-border flex items-center justify-center hover:bg-surface-hover transition-colors z-10"
      >
        {sidebarCollapsed ? (
          <ChevronRight className="w-3 h-3 text-text-tertiary" />
        ) : (
          <ChevronLeft className="w-3 h-3 text-text-tertiary" />
        )}
      </button>
    </motion.aside>
  );
}
