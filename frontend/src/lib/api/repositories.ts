import { apiFetch } from "@/lib/api/client";
import type { CreateRepositoryFromGitHubRequest, Repository } from "@/types/repository";

export const repositoriesApi = {
  list: () => apiFetch<Repository[]>("/repositories"),

  get: (id: string) => apiFetch<Repository>(`/repositories/${id}`),

  createFromGitHub: (payload: CreateRepositoryFromGitHubRequest) =>
    apiFetch<Repository>("/repositories/github", { method: "POST", body: payload }),

  uploadZip: (file: File, name?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (name) formData.append("name", name);
    return apiFetch<Repository>("/repositories/upload", {
      method: "POST",
      body: formData,
      isFormData: true,
    });
  },

  delete: (id: string) => apiFetch<void>(`/repositories/${id}`, { method: "DELETE" }),
};
