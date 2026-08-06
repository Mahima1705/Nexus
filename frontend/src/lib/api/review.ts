import { apiFetch } from "@/lib/api/client";
import type { ReviewHistoryItem } from "@/types/review";

export const reviewApi = {
  reviewSnippet: (source_code: string, language?: string, filename?: string) =>
    apiFetch<ReviewHistoryItem>("/review/snippet", {
      method: "POST",
      body: { source_code, language, filename },
    }),

  reviewFile: (file: File, language?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (language) formData.append("language", language);
    return apiFetch<ReviewHistoryItem>("/review/file", {
      method: "POST",
      body: formData,
      isFormData: true,
    });
  },
};
