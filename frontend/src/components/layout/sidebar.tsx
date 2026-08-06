"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FolderGit2,
  ShieldCheck,
  AlertTriangle,
  User as UserIcon,
  LogOut,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { useAuthStore } from "@/lib/store/auth-store";
import { authApi } from "@/lib/api/auth";
import { toast } from "sonner";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/repositories", label: "Repositories", icon: FolderGit2 },
  { href: "/review", label: "Code Review", icon: ShieldCheck },
  { href: "/errors", label: "Error Analyzer", icon: AlertTriangle },
  { href: "/profile", label: "Profile", icon: UserIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, refreshToken, clear } = useAuthStore();

  const handleLogout = async () => {
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {
      // Best-effort: log the user out locally regardless of whether the server call succeeded.
    } finally {
      clear();
      toast.success("Signed out");
      router.push("/login");
    }
  };

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border bg-card">
      <div className="flex h-16 items-center gap-2 border-b border-border px-6">
        <Sparkles className="h-5 w-5 text-primary" />
        <span className="text-lg font-semibold">Nexus</span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-3">
        <div className="flex items-center justify-between gap-2 rounded-md px-3 py-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{user?.full_name || user?.email}</p>
            {user?.full_name && <p className="truncate text-xs text-muted-foreground">{user.email}</p>}
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            aria-label="Sign out"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
