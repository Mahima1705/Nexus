import Link from "next/link";
import { Files, GitBranch, Layers } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/repository/status-badge";
import type { Repository } from "@/types/repository";

export function RepositoryCard({ repository }: { repository: Repository }) {
  return (
    <Link href={`/repositories/${repository.id}`}>
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardHeader className="flex flex-row items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-semibold">{repository.name}</p>
            {repository.description && (
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{repository.description}</p>
            )}
          </div>
          <StatusBadge status={repository.status} />
        </CardHeader>
        <CardContent className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Files className="h-3.5 w-3.5" /> {repository.total_files} files
          </span>
          <span className="flex items-center gap-1">
            <Layers className="h-3.5 w-3.5" /> {repository.total_chunks} chunks
          </span>
          {repository.default_branch && (
            <span className="flex items-center gap-1">
              <GitBranch className="h-3.5 w-3.5" /> {repository.default_branch}
            </span>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
