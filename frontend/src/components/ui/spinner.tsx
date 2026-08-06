import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-5 w-5 animate-spin text-muted-foreground", className)} />;
}

export function FullPageSpinner() {
  return (
    <div className="flex h-full min-h-[40vh] w-full items-center justify-center">
      <Spinner className="h-8 w-8" />
    </div>
  );
}
