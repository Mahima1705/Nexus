"use client";

import { useState } from "react";
import { AlertCircle, FolderGit2, Plus } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { Button } from "@/components/ui/button";
import { FullPageSpinner } from "@/components/ui/spinner";
import { RepositoryCard } from "@/components/repository/repository-card";
import { UploadRepositoryDialog } from "@/components/repository/upload-repository-dialog";
import { useRepositories } from "@/lib/hooks/use-repositories";

export default function RepositoriesPage() {
  const { repositories, isLoading, error, refetch } = useRepositories();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Repositories"
        description="Upload a ZIP or connect a GitHub repo to start chatting with your code."
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            Add repository
          </Button>
        }
      />

      {isLoading ? (
        <FullPageSpinner />
      ) : error ? (
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
      ) : repositories.length === 0 ? (
        <EmptyState
          icon={FolderGit2}
          title="No repositories yet"
          description="Add your first repository to start indexing it for chat, search, and review."
          action={<Button onClick={() => setDialogOpen(true)}>Add repository</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {repositories.map((repo) => (
            <RepositoryCard key={repo.id} repository={repo} />
          ))}
        </div>
      )}

      <UploadRepositoryDialog open={dialogOpen} onClose={() => setDialogOpen(false)} onCreated={() => refetch()} />
    </div>
  );
}
