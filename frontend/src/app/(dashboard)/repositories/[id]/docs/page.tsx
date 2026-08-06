"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { FileText, Copy } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { MarkdownRenderer } from "@/components/common/markdown-renderer";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { FullPageSpinner } from "@/components/ui/spinner";
import { RepositoryLoadError } from "@/components/repository/repository-load-error";
import { useRepository } from "@/lib/hooks/use-repository";
import { docsApi } from "@/lib/api/docs";
import { ApiError } from "@/lib/api/client";
import { DOC_TYPE_LABELS, type DocumentationHistoryItem, type DocumentationType } from "@/types/docs";

const DOC_TYPES = Object.keys(DOC_TYPE_LABELS) as DocumentationType[];

export default function DocsPage() {
  const { id } = useParams<{ id: string }>();
  const { repository, isLoading, error } = useRepository(id);
  const [docType, setDocType] = useState<DocumentationType>("readme");
  const [result, setResult] = useState<DocumentationHistoryItem | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const doc = await docsApi.generate(id, docType);
      setResult(doc);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error("Couldn't generate documentation", { description: message });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.content);
    toast.success("Copied to clipboard");
  };

  if (isLoading) return <FullPageSpinner />;
  if (error || !repository) return <RepositoryLoadError message={error ?? "Repository not found."} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Documentation Generator"
        description={`Generate docs for ${repository.name}.`}
      />

      <div className="flex flex-col gap-3 sm:flex-row">
        <Select value={docType} onChange={(e) => setDocType(e.target.value as DocumentationType)} className="sm:w-64">
          {DOC_TYPES.map((type) => (
            <option key={type} value={type}>
              {DOC_TYPE_LABELS[type]}
            </option>
          ))}
        </Select>
        <Button onClick={handleGenerate} isLoading={isGenerating}>
          Generate
        </Button>
      </div>

      {!result && !isGenerating && (
        <EmptyState
          icon={FileText}
          title="Generate documentation grounded in your repository"
          description="Choose a document type above and click Generate."
        />
      )}

      {result && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">
                {DOC_TYPE_LABELS[result.doc_type]}
              </p>
              <Button variant="outline" size="sm" onClick={handleCopy}>
                <Copy className="h-3.5 w-3.5" />
                Copy
              </Button>
            </div>
            <MarkdownRenderer content={result.content} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
