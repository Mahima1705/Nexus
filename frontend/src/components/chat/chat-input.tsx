"use client";

import { type KeyboardEvent, useState } from "react";
import { Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export function ChatInput({ onSend, disabled }: { onSend: (content: string) => void; disabled?: boolean }) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2 border-t border-border p-4">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about this codebase... (Shift+Enter for a new line)"
        className="min-h-[44px] resize-none"
        rows={1}
        disabled={disabled}
      />
      <Button onClick={submit} disabled={disabled || !value.trim()} size="icon" aria-label="Send message">
        <Send className="h-4 w-4" />
      </Button>
    </div>
  );
}
