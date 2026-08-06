"use client";

import { User, Mail, Calendar, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/lib/store/auth-store";

function InfoRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 py-3">
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium">{value}</p>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const user = useAuthStore((state) => state.user);

  if (!user) return null;

  return (
    <div className="space-y-6">
      <PageHeader title="Profile" description="Your account details." />

      <Card>
        <CardContent className="p-6">
          <div className="mb-2 flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-lg font-semibold text-primary">
              {(user.full_name || user.email).charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-lg font-semibold">{user.full_name || "Unnamed user"}</p>
              <div className="mt-1 flex gap-2">
                <Badge variant={user.is_active ? "success" : "destructive"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
                {user.is_superuser && <Badge variant="outline">Admin</Badge>}
              </div>
            </div>
          </div>

          <div className="divide-y divide-border">
            <InfoRow icon={User} label="Full name" value={user.full_name || "Not set"} />
            <InfoRow icon={Mail} label="Email" value={user.email} />
            <InfoRow icon={Calendar} label="Member since" value={new Date(user.created_at).toLocaleDateString()} />
            <InfoRow icon={ShieldCheck} label="Account ID" value={user.id} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
