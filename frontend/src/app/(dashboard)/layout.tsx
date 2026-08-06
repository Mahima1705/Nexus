"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { FullPageSpinner } from "@/components/ui/spinner";
import { useAuthStore } from "@/lib/store/auth-store";
import { authApi } from "@/lib/api/auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { accessToken, user, hasHydrated, setUser, clear } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // Wait for zustand's persist middleware to finish reading localStorage —
    // on a fresh page load accessToken briefly holds its initial `null` value
    // even for a returning, already-logged-in user.
    if (!hasHydrated) return;

    if (!accessToken) {
      router.replace("/login");
      return;
    }
    if (user) {
      setIsChecking(false);
      return;
    }
    // Refresh the profile on a hard reload (persisted token, no in-memory user yet).
    authApi
      .me()
      .then((fetchedUser) => {
        setUser(fetchedUser);
        setIsChecking(false);
      })
      .catch(() => {
        clear();
        router.replace("/login");
      });
  }, [hasHydrated, accessToken, user, router, setUser, clear]);

  if (isChecking || !accessToken) {
    return <FullPageSpinner />;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center justify-end border-b border-border px-6">
          <ThemeToggle />
        </header>
        <main className="flex-1 overflow-y-auto p-6 sm:p-8">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
