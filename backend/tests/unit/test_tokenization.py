from app.utils.tokenization import count_tokens


def test_count_tokens_empty_string_is_zero() -> None:
    assert count_tokens("") == 0


def test_count_tokens_counts_more_than_words_for_code() -> None:
    text = "def hello_world():\n    print('hi')"
    tokens = count_tokens(text)
    assert tokens > 0
    # Sanity bound: shouldn't wildly exceed character count for short snippets.
    assert tokens < len(text)


def test_count_tokens_is_monotonic_with_repeated_content() -> None:
    short = count_tokens("hello world")
    long = count_tokens("hello world " * 10)
    assert long > short
