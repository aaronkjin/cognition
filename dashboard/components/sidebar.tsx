"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
/* eslint-disable @next/next/no-img-element */
import { usePathname } from "next/navigation";
import { useLatestRun } from "@/lib/use-status";
import { useTheme } from "@/lib/theme";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  {
    label: "Dashboard",
    href: "/",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="1" y="1" width="7" height="7" rx="1" />
        <rect x="10" y="1" width="7" height="7" rx="1" />
        <rect x="1" y="10" width="7" height="7" rx="1" />
        <rect x="10" y="10" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    label: "Findings",
    href: "/findings",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <line x1="3" y1="4" x2="15" y2="4" />
        <line x1="3" y1="9" x2="15" y2="9" />
        <line x1="3" y1="14" x2="11" y2="14" />
      </svg>
    ),
  },
  {
    label: "Sessions",
    href: "/sessions",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polygon points="5,2 16,9 5,16" />
      </svg>
    ),
  },
  {
    label: "Review",
    href: "/review",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M13 15l3-3-3-3" />
        <path d="M5 15l-3-3 3-3" />
        <polyline points="7 3 11 15" />
      </svg>
    ),
  },
  {
    label: "History",
    href: "/history",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="9" cy="9" r="7" />
        <polyline points="9 5 9 9 12 11" />
      </svg>
    ),
  },
  {
    label: "Eval",
    href: "/eval",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M4 14l3-6 3 4 4-8" />
        <rect x="1" y="1" width="16" height="16" rx="2" />
      </svg>
    ),
  },
  {
    label: "Ops",
    href: "/ops",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="9" cy="9" r="7" />
        <path d="M9 5v4l2.5 2.5" />
        <path d="M3 9h1" />
        <path d="M14 9h1" />
      </svg>
    ),
  },
];

function SunIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="8" cy="8" r="3" />
      <line x1="8" y1="1" x2="8" y2="3" />
      <line x1="8" y1="13" x2="8" y2="15" />
      <line x1="1" y1="8" x2="3" y2="8" />
      <line x1="13" y1="8" x2="15" y2="8" />
      <line x1="3.05" y1="3.05" x2="4.46" y2="4.46" />
      <line x1="11.54" y1="11.54" x2="12.95" y2="12.95" />
      <line x1="3.05" y1="12.95" x2="4.46" y2="11.54" />
      <line x1="11.54" y1="4.46" x2="12.95" y2="3.05" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 8.5A6.5 6.5 0 0 1 7.5 2 5.5 5.5 0 1 0 14 8.5Z" />
    </svg>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { data } = useLatestRun();
  const { theme, toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("sidebar-collapsed");
    if (stored === "true") {
      setCollapsed(true);
    }
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem("sidebar-collapsed", String(collapsed));
  }, [collapsed, mounted]);

  const prCount =
    data?.waves?.reduce(
      (acc, wave) => acc + wave.sessions.filter((s) => s.pr_url).length,
      0,
    ) ?? 0;

  return (
    <aside
      className={`flex h-screen flex-col border-r border-border bg-background transition-all duration-200 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Logo */}
      <div className={`pt-6 pb-2 ${collapsed ? "px-3" : "px-6"}`}>
        {collapsed ? (
          <div className="flex justify-center">
            <img
              src="/cognition-logo.png"
              alt="Cognition"
              width={36}
              height={36}
            />
          </div>
        ) : (
          <div className="flex items-center gap-2.5">
            <img
              src="/cognition-logo.png"
              alt="Cognition"
              width={36}
              height={36}
            />
            <div>
              <h1 className="font-serif text-lg italic text-foreground tracking-tight leading-tight">
                Remediation
              </h1>
              <p className="text-[10px] text-muted-foreground">
                Security Orchestrator
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-6">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center rounded-lg py-2 text-sm font-medium transition-colors ${
                    collapsed ? "justify-center px-2" : "gap-3 px-3"
                  } ${
                    isActive
                      ? "bg-accent text-foreground dark:bg-white/10 dark:text-white"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground dark:hover:bg-white/5"
                  }`}
                  title={collapsed ? item.label : undefined}
                >
                  <span
                    className={
                      isActive ? "text-foreground" : "text-muted-foreground"
                    }
                  >
                    {item.icon}
                  </span>
                  {!collapsed && item.label}
                  {!collapsed && item.label === "Review" && prCount > 0 && (
                    <span className="ml-auto bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center">
                      {prCount}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-3 py-3">
        <div
          className={`flex items-center ${collapsed ? "flex-col gap-2" : "justify-between"}`}
        >
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
            title={
              theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
            }
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>

          {/* Collapse toggle */}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {collapsed ? (
                <>
                  <polyline points="6 4 10 8 6 12" />
                </>
              ) : (
                <>
                  <polyline points="10 4 6 8 10 12" />
                </>
              )}
            </svg>
          </button>
        </div>
        {!collapsed && (
          <p className="mt-2 text-[10px] text-muted-foreground text-center">
            Powered by Devin
          </p>
        )}
      </div>
    </aside>
  );
}
