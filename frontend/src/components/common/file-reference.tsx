"use client";

import { FileCode2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils/cn";

export interface FileReferenceProps {
  filePath: string;
  startLine?: number | null;
  endLine?: number | null;
  score?: number;
  className?: string;
}

export function FileReference({ filePath, startLine, endLine, score, className }: FileReferenceProps) {
  const location = startLine ? `${filePath}:${startLine}${endLine && endLine !== startLine ? `-${endLine}` : ""}` : filePath;

  const handleClick = async () => {
    try {
      await navigator.clipboard.writeText(location);
      toast.success("Copied file reference", { description: location });
    } catch {
      toast.error("Couldn't copy to clipboard");
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      title="Click to copy"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/50 px-2.5 py-1 text-xs font-mono",
        "hover:bg-muted transition-colors",
        className
      )}
    >
      <FileCode2 className="h-3.5 w-3.5 text-muted-foreground" />
      <span>{location}</span>
      {score !== undefined && <span className="text-muted-foreground">· {(score * 100).toFixed(0)}%</span>}
    </button>
  );
}
