"use client";

import Link from "next/link";
import { AlertCircle, FolderGit2, CheckCircle2, Loader2, Files, Plus } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { StatusBadge } from "@/components/repository/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FullPageSpinner } from "@/components/ui/spinner";
import { useRepositories } from "@/lib/hooks/use-repositories";
import { useAuthStore } from "@/lib/store/auth-store";

function StatCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-2xl font-semibold leading-none">{value}</p>
          <p className="mt-1 text-sm text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { repositories, isLoading, error, refetch } = useRepositories();
  const user = useAuthStore((state) => state.user);

  if (isLoading) return <FullPageSpinner />;

  if (error) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Couldn't load your repositories"
        description={error}
        action={
          <Button variant="outline" size="sm" onClick={refetch}>
            Try again
          </Button>
        }
      />
    );
  }

  const readyCount = repositories.filter((r) => r.status === "ready").length;
  const inProgressCount = repositories.filter((r) => !["ready", "failed"].includes(r.status)).length;

  return (
    <div className="space-y-8">
      <PageHeader
        title={`Welcome back${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}`}
        description="Here's what's happening across your repositories."
        actions={
          <Button asChild>
            <Link href="/repositories">
              <Plus className="h-4 w-4" />
              Add repository
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={FolderGit2} label="Repositories" value={repositories.length} />
        <StatCard icon={CheckCircle2} label="Ready to query" value={readyCount} />
        <StatCard icon={Loader2} label="Indexing now" value={inProgressCount} />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent repositories</CardTitle>
          <Link href="/repositories" className="text-sm font-medium text-primary hover:underline">
            View all
          </Link>
        </CardHeader>
        <CardContent>
          {repositories.length === 0 ? (
            <EmptyState
              icon={FolderGit2}
              title="No repositories yet"
              description="Upload a ZIP or connect a GitHub repo to get started."
              action={
                <Button asChild size="sm">
                  <Link href="/repositories">Add your first repository</Link>
                </Button>
              }
            />
          ) : (
            <div className="divide-y divide-border">
              {repositories.slice(0, 5).map((repo) => (
                <Link
                  key={repo.id}
                  href={`/repositories/${repo.id}`}
                  className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0 hover:opacity-80"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{repo.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      <Files className="mr-1 inline h-3 w-3" />
                      {repo.total_files} files · {repo.total_chunks} chunks
                    </p>
                  </div>
                  <StatusBadge status={repo.status} />
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
