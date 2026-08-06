"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store/auth-store";
import { FullPageSpinner } from "@/components/ui/spinner";

export default function RootPage() {
  const router = useRouter();
  const { accessToken, hasHydrated } = useAuthStore();

  useEffect(() => {
    if (!hasHydrated) return;
    router.replace(accessToken ? "/dashboard" : "/login");
  }, [hasHydrated, accessToken, router]);

  return <FullPageSpinner />;
}
