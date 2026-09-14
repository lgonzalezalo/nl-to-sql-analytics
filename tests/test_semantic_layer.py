"""Tests for the semantic layer loader — fast, no network, no LLM.
They act as a first line of defense: if a YAML has a syntax error or is missing
an expected field, this fails in seconds instead of with a confusing traceback
in the middle of a real conversation.
"""
from app.semantic_layer import build_schema, build_examples


def test_schema_is_not_empty():
    schema = build_schema()
    assert len(schema) > 500


def test_schema_includes_confirmed_tables():
    schema = build_schema()
    assert "fact_search_queries" in schema
    assert "fact_clicks" in schema


def test_schema_excludes_tables_pending_modeling():
    """Tables marked PENDING_MODELING (prompts, dim_instances, agg) must not reach
    the LLM prompt yet — this prevents it from inventing columns for a table that
    does not have `columns:` defined yet."""
    schema = build_schema()
    assert "fact_prompts" not in schema
    assert "dim_instances" not in schema


def test_schema_includes_mrr_rule():
    schema = build_schema()
    assert "result_position + 1" in schema


def test_examples_are_not_empty():
    examples = build_examples()
    assert "Example 1:" in examples
    assert len(examples) > 500
