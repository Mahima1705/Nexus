export type MessageRole = "user" | "assistant" | "system";

export interface ReferencedFile {
  file_path: string;
  start_line: number | null;
  end_line: number | null;
  score: number;
}

export interface ChatSession {
  id: string;
  repository_id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  referenced_files: ReferencedFile[] | null;
  created_at: string;
}
