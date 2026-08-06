"use client";

import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Github, Upload } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { repositoriesApi } from "@/lib/api/repositories";
import { ApiError } from "@/lib/api/client";
import type { Repository } from "@/types/repository";

const githubSchema = z.object({
  source_url: z
    .string()
    .min(1, "GitHub URL is required")
    .regex(/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/, "Expected format: https://github.com/<owner>/<repo>"),
  name: z.string().optional(),
});
type GithubFormValues = z.infer<typeof githubSchema>;

export function UploadRepositoryDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (repository: Repository) => void;
}) {
  const [mode, setMode] = useState<"github" | "zip">("github");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<GithubFormValues>({ resolver: zodResolver(githubSchema) });

  const close = () => {
    reset();
    setSelectedFile(null);
    setMode("github");
    onClose();
  };

  const onSubmitGithub = async (values: GithubFormValues) => {
    setIsSubmitting(true);
    try {
      const repository = await repositoriesApi.createFromGitHub(values);
      toast.success("Repository added", { description: "Cloning and indexing has started." });
      onCreated(repository);
      close();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error("Couldn't add repository", { description: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const onSubmitZip = async () => {
    if (!selectedFile) {
      toast.error("Choose a .zip file first");
      return;
    }
    setIsSubmitting(true);
    try {
      const repository = await repositoriesApi.uploadZip(selectedFile);
      toast.success("Repository uploaded", { description: "Extracting and indexing has started." });
      onCreated(repository);
      close();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error("Upload failed", { description: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={close} title="Add a repository" description="Connect a GitHub repo or upload a ZIP archive.">
      <div className="mb-4 flex gap-1 rounded-md bg-muted p-1">
        <button
          type="button"
          onClick={() => setMode("github")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-sm py-1.5 text-sm font-medium transition-colors ${
            mode === "github" ? "bg-card shadow-sm" : "text-muted-foreground"
          }`}
        >
          <Github className="h-4 w-4" /> GitHub
        </button>
        <button
          type="button"
          onClick={() => setMode("zip")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-sm py-1.5 text-sm font-medium transition-colors ${
            mode === "zip" ? "bg-card shadow-sm" : "text-muted-foreground"
          }`}
        >
          <Upload className="h-4 w-4" /> ZIP Upload
        </button>
      </div>

      {mode === "github" ? (
        <form onSubmit={handleSubmit(onSubmitGithub)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="source_url">GitHub URL</Label>
            <Input id="source_url" placeholder="https://github.com/owner/repo" {...register("source_url")} />
            {errors.source_url && <p className="text-sm text-destructive">{errors.source_url.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Display name (optional)</Label>
            <Input id="name" placeholder="Defaults to the repo name" {...register("name")} />
          </div>
          <Button type="submit" className="w-full" isLoading={isSubmitting}>
            Add repository
          </Button>
        </form>
      ) : (
        <div className="space-y-4">
          <div
            onClick={() => fileInputRef.current?.click()}
            className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border p-8 text-center hover:bg-muted/50"
          >
            <Upload className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium">{selectedFile ? selectedFile.name : "Click to choose a .zip file"}</p>
            <p className="text-xs text-muted-foreground">Max 200MB</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          />
          <Button className="w-full" isLoading={isSubmitting} onClick={onSubmitZip} disabled={!selectedFile}>
            Upload repository
          </Button>
        </div>
      )}
    </Dialog>
  );
}
