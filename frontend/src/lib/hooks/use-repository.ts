"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { repositoriesApi } from "@/lib/api/repositories";
import type { Repository } from "@/types/repository";

const IN_PROGRESS_STATUSES = new Set(["pending", "cloning", "extracting", "indexing"]);
const POLL_INTERVAL_MS = 2500;

export function useRepository(repositoryId: string) {
  const [repository, setRepository] = useState<Repository | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchRepository = useCallback(
    async (isInitial = false) => {
      if (isInitial) setIsLoading(true);
      try {
        const data = await repositoriesApi.get(repositoryId);
        setRepository(data);
        setError(null);
      } catch {
        setError("Couldn't load this repository.");
      } finally {
        if (isInitial) setIsLoading(false);
      }
    },
    [repositoryId]
  );

  useEffect(() => {
    fetchRepository(true);
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, [fetchRepository]);

  useEffect(() => {
    if (!repository || !IN_PROGRESS_STATUSES.has(repository.status)) return;

    pollTimeoutRef.current = setTimeout(() => fetchRepository(false), POLL_INTERVAL_MS);
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, [repository, fetchRepository]);

  return { repository, isLoading, error, refetch: () => fetchRepository(false) };
}
