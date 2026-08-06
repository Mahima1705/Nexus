export type ReviewInputType = "snippet" | "file";

export interface ReviewFinding {
  description: string;
  line?: number | null;
  severity?: "low" | "medium" | "high";
}

export interface ReviewResult {
  bugs: ReviewFinding[];
  security_issues: ReviewFinding[];
  code_smells: ReviewFinding[];
  performance_suggestions: ReviewFinding[];
  best_practices: ReviewFinding[];
}

export interface ReviewHistoryItem {
  id: string;
  repository_id: string | null;
  input_type: ReviewInputType;
  input_reference: string | null;
  language: string | null;
  review_result: ReviewResult;
  created_at: string;
}
