"use client";

import { Plus, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";
import type { ChatSession } from "@/types/chat";

export function SessionList({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  isCreating,
}: {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelect: (session: ChatSession) => void;
  onCreate: () => void;
  isCreating: boolean;
}) {
  return (
    <div className="flex h-full w-64 shrink-0 flex-col border-r border-border">
      <div className="p-3">
        <Button variant="outline" className="w-full" onClick={onCreate} isLoading={isCreating}>
          <Plus className="h-4 w-4" />
          New chat
        </Button>
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto p-3 pt-0">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSelect(session)}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors",
              session.id === activeSessionId
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <MessageSquare className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{session.title || "Untitled chat"}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
