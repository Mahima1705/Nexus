import { apiFetch, apiStream, type StreamHandlers } from "@/lib/api/client";
import type { ChatSession, Message } from "@/types/chat";

export const chatApi = {
  listSessions: (repositoryId: string) =>
    apiFetch<ChatSession[]>(`/repositories/${repositoryId}/sessions`),

  createSession: (repositoryId: string, title?: string) =>
    apiFetch<ChatSession>(`/repositories/${repositoryId}/sessions`, {
      method: "POST",
      body: { title },
    }),

  listMessages: (sessionId: string) => apiFetch<Message[]>(`/sessions/${sessionId}/messages`),

  sendMessage: (sessionId: string, content: string) =>
    apiFetch<Message>(`/sessions/${sessionId}/messages`, {
      method: "POST",
      body: { content },
    }),

  streamMessage: (sessionId: string, content: string, handlers: StreamHandlers<Message>) =>
    apiStream<Message>(`/sessions/${sessionId}/messages/stream`, { content }, handlers),
};
