import { Bot, User } from "lucide-react";
import { MarkdownRenderer } from "@/components/common/markdown-renderer";
import { FileReference } from "@/components/common/file-reference";
import { cn } from "@/lib/utils/cn";
import type { Message } from "@/types/chat";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className={cn("flex max-w-[80%] flex-col gap-2", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-lg px-4 py-2.5 text-sm",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : message.content ? (
            <MarkdownRenderer content={message.content} />
          ) : (
            <span className="flex gap-1 py-1" aria-label="Assistant is responding">
              <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-muted-foreground" />
              <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-muted-foreground [animation-delay:0.2s]" />
              <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-muted-foreground [animation-delay:0.4s]" />
            </span>
          )}
        </div>
        {message.referenced_files && message.referenced_files.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.referenced_files.map((ref, i) => (
              <FileReference
                key={`${ref.file_path}-${i}`}
                filePath={ref.file_path}
                startLine={ref.start_line}
                endLine={ref.end_line}
                score={ref.score}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
