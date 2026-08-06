import { apiFetch } from "@/lib/api/client";
import type { DocumentationHistoryItem, DocumentationType } from "@/types/docs";

export const docsApi = {
  generate: (repositoryId: string, docType: DocumentationType) =>
    apiFetch<DocumentationHistoryItem>(`/docs/repositories/${repositoryId}/generate`, {
      method: "POST",
      body: { doc_type: docType },
    }),
};
