import { apiFetch } from "@/lib/api/client";
import type { ErrorAnalysisResponse } from "@/types/errors";

export const errorsApi = {
  analyze: (error_text: string, repository_id?: string) =>
    apiFetch<ErrorAnalysisResponse>("/errors/analyze", {
      method: "POST",
      body: { error_text, repository_id },
    }),
};
