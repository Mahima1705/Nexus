"use client";

import { useState } from "react";
import { AlertTriangle, Lightbulb, Wrench, FileWarning } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { FileReference } from "@/components/common/file-reference";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useRepositories } from "@/lib/hooks/use-repositories";
import { errorsApi } from "@/lib/api/errors";
import { ApiError } from "@/lib/api/client";
import type { ErrorAnalysisResponse } from "@/types/errors";

export default function ErrorsPage() {
  const { repositories, error: repositoriesError } = useRepositories();
  const [errorText, setErrorText] = useState("");
  const [repositoryId, setRepositoryId] = useState<string>("");
  const [result, setResult] = useState<ErrorAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const readyRepositories = repositories.filter((r) => r.status === "ready");

  const handleAnalyze = async () => {
    if (!errorText.trim()) return;
    setIsAnalyzing(true);
    setResult(null);
    try {
      const response = await errorsApi.analyze(errorText.trim(), repositoryId || undefined);
      setResult(response);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error("Analysis failed", { description: message });
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Error & Log Analyzer" description="Paste a stack trace, exception, or log output for a plain-English explanation." />

      <Card>
        <CardContent className="space-y-4 p-6">
          <Textarea
            value={errorText}
            onChange={(e) => setErrorText(e.target.value)}
            placeholder="Paste your error, exception, or stack trace here..."
            className="min-h-[200px] font-mono text-sm"
          />
          <div className="max-w-sm space-y-2">
            <Label htmlFor="repository">Repository context (optional)</Label>
            <Select
              id="repository"
              value={repositoryId}
              onChange={(e) => setRepositoryId(e.target.value)}
              disabled={!!repositoriesError}
            >
              <option value="">No repository context</option>
              {readyRepositories.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.name}
                </option>
              ))}
            </Select>
            {repositoriesError && (
              <p className="text-xs text-muted-foreground">Couldn&apos;t load your repositories.</p>
            )}
          </div>
          <Button onClick={handleAnalyze} isLoading={isAnalyzing} disabled={!errorText.trim()}>
            Analyze error
          </Button>
        </CardContent>
      </Card>

      {!result && !isAnalyzing && (
        <EmptyState
          icon={AlertTriangle}
          title="No analysis yet"
          description="Paste an error above to get an explanation and debugging suggestions."
        />
      )}

      {result && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Explanation</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">{result.explanation}</CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0">
              <FileWarning className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">Likely cause</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">{result.likely_cause}</CardContent>
          </Card>

          {result.relevant_files.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Relevant files</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {result.relevant_files.map((file) => (
                  <FileReference key={file} filePath={file} />
                ))}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0">
              <Lightbulb className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">Debugging suggestions</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {result.debugging_suggestions.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0">
              <Wrench className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">Possible fixes</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {result.possible_fixes.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
