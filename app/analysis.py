"""Deterministic calculations (Python, not LLM) over the results of a query.

Core principle of the whole project: never let the LLM "compute" or "compare"
numbers itself from a large table — it is given the numbers already computed and
only writes them up as text.
"""
from collections import Counter
from datetime import date, datetime

SUMMARY_ROW_THRESHOLD = 8


def summarize_multirow(rows, columns) -> dict:
    total_rows = len(rows)
    summary = {"total_rows": total_rows}

    text_columns = [
        (idx, name) for idx, name in enumerate(columns)
        if isinstance(rows[0][idx], str)
    ]
    if text_columns:
        idx_cat, col_name = text_columns[-1]
        values = [row[idx_cat] for row in rows]
        counts = Counter(values)
        most_common, times = counts.most_common(1)[0]
        summary[f"most_frequent_value_in_{col_name}"] = most_common
        summary[f"times_it_appears_{col_name}"] = times
        summary[f"distinct_values_in_{col_name}"] = len(counts)

    for idx, col_name in enumerate(columns):
        non_null_values = [
            r for r in rows if r[idx] is not None and isinstance(r[idx], (int, float))
        ]
        if non_null_values:
            summary[f"row_with_max_{col_name}"] = max(non_null_values, key=lambda r: r[idx])
            summary[f"row_with_min_{col_name}"] = min(non_null_values, key=lambda r: r[idx])
            break

    if any(isinstance(r[0], (date, datetime)) for r in rows):
        summary["note"] = (
            "The last day of the series may be incomplete (current day), "
            "do not treat it as comparable to full days."
        )

    return summary
