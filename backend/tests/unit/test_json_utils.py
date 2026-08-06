import json

import pytest

from app.utils.json_utils import extract_json


def test_extract_json_parses_plain_json() -> None:
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_markdown_fence() -> None:
    text = '```json\n{"a": 1, "b": [1, 2]}\n```'
    assert extract_json(text) == {"a": 1, "b": [1, 2]}


def test_extract_json_strips_fence_without_json_tag() -> None:
    text = '```\n{"a": 1}\n```'
    assert extract_json(text) == {"a": 1}


def test_extract_json_extracts_object_from_surrounding_prose() -> None:
    text = 'Sure, here is the analysis:\n{"a": 1}\nLet me know if you need more.'
    assert extract_json(text) == {"a": 1}


def test_extract_json_raises_on_unparseable_text() -> None:
    with pytest.raises(json.JSONDecodeError):
        extract_json("this is not json at all")
