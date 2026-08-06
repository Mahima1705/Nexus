import { apiFetch } from "@/lib/api/client";
import type { SearchResponse } from "@/types/search";

export const searchApi = {
  search: (repositoryId: string, query: string) =>
    apiFetch<SearchResponse>(`/repositories/${repositoryId}/search`, {
      method: "POST",
      body: { query },
    }),
};
