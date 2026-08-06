"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Search as SearchIcon } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { FileReference } from "@/components/common/file-reference";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FullPageSpinner } from "@/components/ui/spinner";
import { RepositoryLoadError } from "@/components/repository/repository-load-error";
import { useRepository } from "@/lib/hooks/use-repository";
import { searchApi } from "@/lib/api/search";
import { ApiError } from "@/lib/api/client";
import type { SearchResponse } from "@/types/search";

export default function SearchPage() {
  const { id } = useParams<{ id: string }>();
  const { repository, isLoading, error } = useRepository(id);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsSearching(true);
    setResult(null);
    try {
      const response = await searchApi.search(id, query.trim());
      setResult(response);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error("Search failed", { description: message });
    } finally {
      setIsSearching(false);
    }
  };

  if (isLoading) return <FullPageSpinner />;
  if (error || !repository) return <RepositoryLoadError message={error ?? "Repository not found."} />;

  return (
    <div className="space-y-6">
      <PageHeader title="Smart Code Search" description={`Find where to make a change in ${repository.name}.`} />

      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Where should I add Google login?"
        />
        <Button onClick={handleSearch} isLoading={isSearching} disabled={!query.trim()}>
          <SearchIcon className="h-4 w-4" />
          Search
        </Button>
      </div>

      {!result && !isSearching && (
        <EmptyState
          icon={SearchIcon}
          title="Search your codebase in plain English"
          description='Try "where are email APIs?" or "which module creates orders?"'
        />
      )}

      {result && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Explanation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>{result.explanation}</p>
              {result.reasoning && <p className="text-muted-foreground">{result.reasoning}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Relevant files</CardTitle>
            </CardHeader>
            <CardContent>
              {result.relevant_files.length === 0 ? (
                <p className="text-sm text-muted-foreground">No specific files were identified.</p>
              ) : (
                <div className="space-y-3">
                  {result.relevant_files.map((file, i) => (
                    <div key={`${file.file_path}-${i}`} className="space-y-1">
                      <FileReference filePath={file.file_path} />
                      <p className="pl-1 text-sm text-muted-foreground">{file.reason}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
