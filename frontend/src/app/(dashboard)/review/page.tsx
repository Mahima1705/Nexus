"use client";

import { useRef, useState } from "react";
import { ShieldCheck, Upload } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { FindingsList } from "@/components/review/findings-list";
import { reviewApi } from "@/lib/api/review";
import { ApiError } from "@/lib/api/client";
import type { ReviewHistoryItem } from "@/types/review";

export default function ReviewPage() {
  const [mode, setMode] = useState<"snippet" | "file">("snippet");
  const [sourceCode, setSourceCode] = useState("");
  const [language, setLanguage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ReviewHistoryItem | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleReview = async () => {
    setIsReviewing(true);
    setResult(null);
    try {
      const review =
        mode === "snippet"
          ? await reviewApi.reviewSnippet(sourceCode, language || undefined)
          : await reviewApi.reviewFile(selectedFile as File, language || undefined);
      setResult(review);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error("Review failed", { description: message });
    } finally {
      setIsReviewing(false);
    }
  };

  const canSubmit = mode === "snippet" ? sourceCode.trim().length > 0 : selectedFile !== null;

  return (
    <div className="space-y-6">
      <PageHeader title="AI Code Reviewer" description="Paste a snippet or upload a file for bugs, security issues, and more." />

      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="flex gap-1 rounded-md bg-muted p-1">
            <button
              type="button"
              onClick={() => setMode("snippet")}
              className={`flex-1 rounded-sm py-1.5 text-sm font-medium transition-colors ${
                mode === "snippet" ? "bg-card shadow-sm" : "text-muted-foreground"
              }`}
            >
              Paste code
            </button>
            <button
              type="button"
              onClick={() => setMode("file")}
              className={`flex-1 rounded-sm py-1.5 text-sm font-medium transition-colors ${
                mode === "file" ? "bg-card shadow-sm" : "text-muted-foreground"
              }`}
            >
              Upload file
            </button>
          </div>

          {mode === "snippet" ? (
            <Textarea
              value={sourceCode}
              onChange={(e) => setSourceCode(e.target.value)}
              placeholder="Paste your code here..."
              className="min-h-[240px] font-mono text-sm"
            />
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border p-8 text-center hover:bg-muted/50"
            >
              <Upload className="h-6 w-6 text-muted-foreground" />
              <p className="text-sm font-medium">{selectedFile ? selectedFile.name : "Click to choose a file"}</p>
              <p className="text-xs text-muted-foreground">Max 200KB</p>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              />
            </div>
          )}

          <div className="max-w-xs space-y-2">
            <Label htmlFor="language">Language (optional)</Label>
            <Input id="language" value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="python" />
          </div>

          <Button onClick={handleReview} isLoading={isReviewing} disabled={!canSubmit}>
            Review code
          </Button>
        </CardContent>
      </Card>

      {!result && !isReviewing && (
        <EmptyState icon={ShieldCheck} title="No review yet" description="Submit code above to get AI-powered feedback." />
      )}

      {result && <FindingsList result={result.review_result} />}
    </div>
  );
}
