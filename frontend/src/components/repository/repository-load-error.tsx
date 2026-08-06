import Link from "next/link";
import { AlertCircle } from "lucide-react";
import { EmptyState } from "@/components/common/empty-state";
import { Button } from "@/components/ui/button";

export function RepositoryLoadError({ message }: { message: string }) {
  return (
    <EmptyState
      icon={AlertCircle}
      title="Couldn't load this repository"
      description={message}
      action={
        <Button asChild variant="outline" size="sm">
          <Link href="/repositories">Back to repositories</Link>
        </Button>
      }
    />
  );
}
