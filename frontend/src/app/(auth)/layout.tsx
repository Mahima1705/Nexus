"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { useAuthStore } from "@/lib/store/auth-store";
import { FullPageSpinner } from "@/components/ui/spinner";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { accessToken, hasHydrated } = useAuthStore();

  useEffect(() => {
    if (!hasHydrated) return;
    if (accessToken) router.replace("/dashboard");
  }, [hasHydrated, accessToken, router]);

  // Avoid flashing the login/register form for an already-authenticated user
  // while the redirect above is in flight.
  if (!hasHydrated || accessToken) return <FullPageSpinner />;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 px-4 py-12">
      <div className="mb-8 flex items-center gap-2">
        <Sparkles className="h-6 w-6 text-primary" />
        <span className="text-xl font-semibold">Nexus</span>
      </div>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  );
}
