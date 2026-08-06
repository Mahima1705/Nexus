"""Token counting shared by the chunker and (later) the embedding/LLM services.

Uses tiktoken's cl100k_base encoding — the same tokenizer OpenAI's embedding and
GPT-4 family models use — so chunk sizes are measured in the units that actually
matter for staying under a model's context window, not a rough character count.
"""
from functools import lru_cache

import tiktoken


@lru_cache(maxsize=1)
def _get_encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_get_encoding().encode(text, disallowed_special=()))
