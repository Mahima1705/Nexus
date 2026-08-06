export type DocumentationType =
  | "readme"
  | "project_overview"
  | "folder_structure"
  | "api_summary"
  | "installation_guide"
  | "env_variables"
  | "full";

export interface DocumentationHistoryItem {
  id: string;
  repository_id: string;
  doc_type: DocumentationType;
  content: string;
  created_at: string;
}

export const DOC_TYPE_LABELS: Record<DocumentationType, string> = {
  readme: "README",
  project_overview: "Project Overview",
  folder_structure: "Folder Structure",
  api_summary: "API Summary",
  installation_guide: "Installation Guide",
  env_variables: "Environment Variables",
  full: "Full Documentation",
};
