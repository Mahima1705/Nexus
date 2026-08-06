"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { MessageSquare, Search, FileText, Trash2, Files, Layers, GitBranch, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/repository/status-badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { FullPageSpinner } from "@/components/ui/spinner";
import { RepositoryLoadError } from "@/components/repository/repository-load-error";
import { useRepository } from "@/lib/hooks/use-repository";
import { repositoriesApi } from "@/lib/api/repositories";
import { ApiError } from "@/lib/api/client";

const FEATURE_LINKS = [
  { key: "chat", label: "Chat", description: "Ask questions about this codebase", icon: MessageSquare },
  { key: "search", label: "Smart Search", description: "Find where to make a change", icon: Search },
  { key: "docs", label: "Documentation", description: "Generate README, API docs, and more", icon: FileText },
];

export default function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { repository, isLoading, error } = useRepository(id);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  if (isLoading) return <FullPageSpinner />;
  if (error || !repository) return <RepositoryLoadError message={error ?? "Repository not found."} />;

  const isReady = repository.status === "ready";

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await repositoriesApi.delete(repository.id);
      toast.success("Repository deleted");
      router.push("/repositories");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error("Couldn't delete repository", { description: message });
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={repository.name}
        description={repository.description ?? undefined}
        actions={
          <>
            <StatusBadge status={repository.status} />
            <Button variant="outline" size="icon" onClick={() => setDeleteOpen(true)} aria-label="Delete repository">
              <Trash2 className="h-4 w-4" />
            </Button>
          </>
        }
      />

      {repository.status === "failed" && repository.status_message && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="p-4 text-sm text-destructive">{repository.status_message}</CardContent>
        </Card>
      )}

      {!isReady && repository.status !== "failed" && (
        <Card className="border-warning/50 bg-warning/5">
          <CardContent className="p-4 text-sm text-warning">
            This repository is still being processed ({repository.status}). Chat, search, and documentation will be
            available once indexing completes.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Files className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{repository.total_files} files</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Layers className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{repository.total_chunks} chunks</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <GitBranch className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{repository.default_branch ?? repository.source_type}</span>
          </CardContent>
        </Card>
      </div>

      {repository.source_url && (
        <a
          href={repository.source_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
        >
          {repository.source_url}
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        {FEATURE_LINKS.map((feature) => {
          const Icon = feature.icon;
          const content = (
            <Card className={isReady ? "h-full transition-shadow hover:shadow-md" : "h-full opacity-50"}>
              <CardHeader className="flex flex-row items-center gap-3 space-y-0">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-base">{feature.label}</CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </div>
              </CardHeader>
            </Card>
          );
          return isReady ? (
            <Link key={feature.key} href={`/repositories/${repository.id}/${feature.key}`}>
              {content}
            </Link>
          ) : (
            <div key={feature.key}>{content}</div>
          );
        })}
      </div>

      <Dialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Delete repository?"
        description={`This permanently removes "${repository.name}" and its indexed data. This can't be undone.`}
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isDeleting} onClick={handleDelete}>
              Delete
            </Button>
          </>
        }
      />
    </div>
  );
}
