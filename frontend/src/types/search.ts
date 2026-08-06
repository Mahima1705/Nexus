export interface RelevantFile {
  file_path: string;
  reason: string;
}

export interface SearchResponse {
  relevant_files: RelevantFile[];
  explanation: string;
  reasoning: string;
}
