export type RepositorySourceType = "github" | "zip";

export type RepositoryStatus =
  | "pending"
  | "cloning"
  | "extracting"
  | "indexing"
  | "ready"
  | "failed";

export interface Repository {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  source_type: RepositorySourceType;
  source_url: string | null;
  default_branch: string | null;
  status: RepositoryStatus;
  status_message: string | null;
  total_files: number;
  total_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface CreateRepositoryFromGitHubRequest {
  source_url: string;
  name?: string;
  description?: string;
}
