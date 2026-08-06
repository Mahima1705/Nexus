"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { repositoriesApi } from "@/lib/api/repositories";
import type { Repository } from "@/types/repository";

const IN_PROGRESS_STATUSES = new Set(["pending", "cloning", "extracting", "indexing"]);
const POLL_INTERVAL_MS = 3000;

export function useRepositories() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchRepositories = useCallback(async (isInitial = false) => {
    if (isInitial) setIsLoading(true);
    try {
      const data = await repositoriesApi.list();
      setRepositories(data);
      setError(null);
    } catch {
      setError("Couldn't load repositories.");
    } finally {
      if (isInitial) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRepositories(true);
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, [fetchRepositories]);

  // While any repository is still being cloned/extracted/indexed, poll for updates
  // so the UI reflects status changes (e.g. "indexing" -> "ready") without a manual refresh.
  useEffect(() => {
    const hasInProgress = repositories.some((repo) => IN_PROGRESS_STATUSES.has(repo.status));
    if (!hasInProgress) return;

    pollTimeoutRef.current = setTimeout(() => fetchRepositories(false), POLL_INTERVAL_MS);
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, [repositories, fetchRepositories]);

  return { repositories, isLoading, error, refetch: () => fetchRepositories(false) };
}
