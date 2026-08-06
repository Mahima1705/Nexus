"""Prompt templates for the Documentation Generator feature."""

DOCUMENTATION_SYSTEM_PROMPT = """You are Nexus's Documentation Generator. Write clear, accurate, well-formatted Markdown documentation strictly grounded in the provided repository context. Never invent files, dependencies, endpoints, or features that aren't evidenced in the context — if something can't be determined from the context, say so explicitly rather than guessing."""

DOC_TYPE_INSTRUCTIONS: dict[str, str] = {
    "readme": (
        "Generate a complete, professional README.md in Markdown for this repository: title, "
        "description, key features, installation, and usage sections."
    ),
    "project_overview": (
        "Write a concise Project Overview in Markdown: what this project does, its architecture "
        "at a high level, and its main components."
    ),
    "api_summary": (
        "Write an API Summary in Markdown, listing the API endpoints/routes identifiable from the "
        "repository context, with their purpose. If no API routes are visible, say so explicitly."
    ),
    "installation_guide": (
        "Write an Installation Guide in Markdown: prerequisites, setup steps, and how to run the "
        "project, based on the repository context (e.g. dependency files, Dockerfiles)."
    ),
    "env_variables": (
        "List and explain the environment variables this project uses, based on the repository "
        "context (e.g. .env.example, config files). If none are visible, say so explicitly."
    ),
    "full": (
        "Generate complete documentation covering: project overview, architecture, installation, "
        "usage, API summary, and environment variables — using clear Markdown section headings."
    ),
}


def build_documentation_user_prompt(doc_type: str, repository_prompt: str, context_prompt: str) -> str:
    instruction = DOC_TYPE_INSTRUCTIONS.get(doc_type, "Generate helpful documentation for this repository.")
    return f"{repository_prompt}\n\nRepository context:\n{context_prompt}\n\nTask: {instruction}"
