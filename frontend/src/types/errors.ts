export interface ErrorAnalysisResponse {
  explanation: string;
  likely_cause: string;
  relevant_files: string[];
  debugging_suggestions: string[];
  possible_fixes: string[];
}
