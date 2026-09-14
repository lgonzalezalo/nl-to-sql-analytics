"""Regression battery: each case here is a REAL failure  already saw and fixed
during the development of the POC. If a future change to the semantic layer
breaks one of these, this test catches it before it reaches production.

It does not check that the SQL is "perfect"  — it checks
that it contains the key fragments that prove the correct business rule was
applied.
"""
import pytest
from app.llm_service import generate_sql
from app.sql_guard import enforce_limit_from_question, is_sql_safe

KNOWN_CASES = [
    # (question, fragment(s) the SQL MUST contain, lowercased)
    ("How many searches had a fallback?", ["num_results = -1"]),
    ("How many searches had no results?", ["num_results = 0"]),
    ("What is the no-results rate in deployment_a?", ["num_results = 0", "count(*)"]),
    (
        "in DEPLOYMENT_A, top origin category per instance in the last 3 days",
        ["row_number()", "partition by"],
    ),
    (
        "combined CTR in the last 10 days for categories category1, category2",
        ["like"],
    ),
        ("Total searches in DEPLOYMENT_B in the last 7 days", ["num_results <> -1"]),
]


@pytest.mark.parametrize("question,expected_fragments", KNOWN_CASES)
def test_generates_sql_with_correct_rule(question, expected_fragments):
    sql = generate_sql(question, history=[])
    sql_lower = sql.lower()
    for fragment in expected_fragments:
        assert fragment in sql_lower, (
            f"Question: {question!r}\nGenerated SQL: {sql}\n"
            f"Does not contain the expected fragment: {fragment!r}"
        )


def test_never_uses_in_for_multiple_categories():
    """Regression for the case: 'daily evolution of categories in (...)' produced
    'query_origin IN (...)' with exact names, instead of LIKE with OR."""
    question = "daily evolution of categories category1, category2, category3"
    sql = generate_sql(question, history=[])
    assert "query_origin in (" not in sql.lower(), (
        f"The SQL uses 'query_origin IN (...)', forbidden by the semantic layer:\n{sql}"
    )


def test_top_n_is_enforced_in_code():
    """Even if the LLM ignores the 'top 10', enforce_limit_from_question must force it."""
    fake_sql = "SELECT query_verbatim, COUNT(*) AS times FROM fact_search_queries GROUP BY query_verbatim ORDER BY times DESC LIMIT 100"
    question = "top 10 no-results terms for client client_demo"
    result = enforce_limit_from_question(fake_sql, question)
    assert "limit 10" in result.lower()


@pytest.mark.parametrize(
    "dangerous_sql",
    [
        "DROP TABLE fact_search_queries",
        "DELETE FROM fact_clicks WHERE 1=1",
        "INSERT INTO fact_search_queries VALUES (1)",
        "ALTER TABLE fact_clicks ADD COLUMN x String",
    ],
)
def test_blocks_dangerous_sql(dangerous_sql):
    assert is_sql_safe(dangerous_sql) is False


def test_allows_read_only_sql():
    assert is_sql_safe("SELECT COUNT(*) FROM fact_search_queries") is True
