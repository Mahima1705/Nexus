import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { RepositoryStatus } from "@/types/repository";

const STATUS_CONFIG: Record<RepositoryStatus, { label: string; variant: "success" | "warning" | "destructive" | "default"; spinning?: boolean }> = {
  pending: { label: "Pending", variant: "default", spinning: true },
  cloning: { label: "Cloning", variant: "warning", spinning: true },
  extracting: { label: "Extracting", variant: "warning", spinning: true },
  indexing: { label: "Indexing", variant: "warning", spinning: true },
  ready: { label: "Ready", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
};

export function StatusBadge({ status }: { status: RepositoryStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <Badge variant={config.variant} className="gap-1">
      {config.spinning && <Loader2 className="h-3 w-3 animate-spin" />}
      {config.label}
    </Badge>
  );
}
