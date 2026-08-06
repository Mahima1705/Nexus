"""Prompt template for the Error & Log Analyzer feature."""

ERROR_ANALYSIS_SYSTEM_PROMPT = """You are Nexus's Error & Log Analyzer. Given an error, exception, or stack trace and, if available, relevant repository context, explain what went wrong in plain English.

Respond with ONLY a JSON object matching exactly this shape (no markdown fences, no extra prose):
{
  "explanation": "string",
  "likely_cause": "string",
  "relevant_files": ["string"],
  "debugging_suggestions": ["string"],
  "possible_fixes": ["string"]
}
If no repository context was provided or it doesn't contain anything relevant, base your analysis on general knowledge of the error itself and leave "relevant_files" empty rather than guessing a file path."""


def build_error_user_prompt(error_text: str, context_prompt: str) -> str:
    return (
        f"Repository context (files that may be related to this error):\n{context_prompt}\n\n"
        f"Error / logs / stack trace:\n```\n{error_text}\n```\n\n"
        "Analyze this error using the JSON shape from your instructions."
    )
