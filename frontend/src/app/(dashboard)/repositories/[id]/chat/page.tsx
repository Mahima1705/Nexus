"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { SessionList } from "@/components/chat/session-list";
import { MessageBubble } from "@/components/chat/message-bubble";
import { ChatInput } from "@/components/chat/chat-input";
import { EmptyState } from "@/components/common/empty-state";
import { FullPageSpinner } from "@/components/ui/spinner";
import { RepositoryLoadError } from "@/components/repository/repository-load-error";
import { chatApi } from "@/lib/api/chat";
import { useRepository } from "@/lib/hooks/use-repository";
import type { ChatSession, Message } from "@/types/chat";

const STREAMING_PLACEHOLDER_ID = "streaming-assistant-placeholder";

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const { repository, isLoading: isRepoLoading, error: repoError } = useRepository(id);

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatApi
      .listSessions(id)
      .then((data) => {
        setSessions(data);
        const [firstSession] = data;
        if (firstSession) setActiveSession(firstSession);
      })
      .catch(() => toast.error("Couldn't load chat sessions"))
      .finally(() => setIsLoadingSessions(false));
  }, [id]);

  useEffect(() => {
    if (!activeSession) {
      setMessages([]);
      return;
    }
    setIsLoadingMessages(true);
    chatApi
      .listMessages(activeSession.id)
      .then(setMessages)
      .catch(() => toast.error("Couldn't load messages"))
      .finally(() => setIsLoadingMessages(false));
  }, [activeSession]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  const handleCreateSession = async () => {
    setIsCreatingSession(true);
    try {
      const session = await chatApi.createSession(id);
      setSessions((prev) => [session, ...prev]);
      setActiveSession(session);
    } catch {
      toast.error("Couldn't start a new chat");
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleSend = async (content: string) => {
    let session = activeSession;
    if (!session) {
      try {
        session = await chatApi.createSession(id, content.slice(0, 60));
        setSessions((prev) => [session as ChatSession, ...prev]);
        setActiveSession(session);
      } catch {
        toast.error("Couldn't start a new chat");
        return;
      }
    }

    const optimisticUserMessage: Message = {
      id: `optimistic-${Date.now()}`,
      session_id: session.id,
      role: "user",
      content,
      referenced_files: null,
      created_at: new Date().toISOString(),
    };
    const streamingPlaceholder: Message = {
      id: STREAMING_PLACEHOLDER_ID,
      session_id: session.id,
      role: "assistant",
      content: "",
      referenced_files: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUserMessage, streamingPlaceholder]);
    setIsSending(true);

    await chatApi.streamMessage(session.id, content, {
      onChunk: (delta) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === STREAMING_PLACEHOLDER_ID ? { ...m, content: m.content + delta } : m))
        );
      },
      onDone: (finalMessage) => {
        setMessages((prev) => prev.map((m) => (m.id === STREAMING_PLACEHOLDER_ID ? finalMessage : m)));
        setIsSending(false);
      },
      onError: (errorMessage) => {
        // The user's question was already persisted server-side before streaming
        // started, so only the (empty/partial) assistant placeholder is removed —
        // the question itself stays visible, matching what's actually saved.
        toast.error("Message failed", { description: errorMessage });
        setMessages((prev) => prev.filter((m) => m.id !== STREAMING_PLACEHOLDER_ID));
        setIsSending(false);
      },
    });
  };

  if (isRepoLoading || isLoadingSessions) return <FullPageSpinner />;
  if (repoError || !repository) return <RepositoryLoadError message={repoError ?? "Repository not found."} />;

  return (
    <div className="flex h-[calc(100vh-8rem)] overflow-hidden rounded-lg border border-border">
      <SessionList
        sessions={sessions}
        activeSessionId={activeSession?.id ?? null}
        onSelect={setActiveSession}
        onCreate={handleCreateSession}
        isCreating={isCreatingSession}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="border-b border-border px-4 py-3">
          <p className="text-sm font-medium">{repository?.name}</p>
          <p className="text-xs text-muted-foreground">{activeSession?.title || "New conversation"}</p>
        </div>

        <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto p-4 scrollbar-thin">
          {isLoadingMessages ? (
            <FullPageSpinner />
          ) : messages.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="Ask anything about this repository"
              description='Try "How does authentication work?" or "Where is the payment flow?"'
              className="h-full border-none"
            />
          ) : (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          )}
        </div>

        <ChatInput onSend={handleSend} disabled={isSending} />
      </div>
    </div>
  );
}
