"""ASCII charts in the terminal (plotext). Auto-detects:
  - date + category -> one line per category (split)
  - date only       -> a single line
  - category only   -> horizontal bars
"""
from datetime import date, datetime
import plotext as pltxt
# failed to intepret order in spanish so adding in Spanish as well  
def wants_chart(question: str) -> bool:
    keywords = ["chart", "graph", "plot", "visualize", "visualise", "draw", "grafico", "gráfico", "diagrama", "visualizar", "visualiza", "dibuja", "dashboard"
                ]
    question_lower = question.lower()
    return any(k in question_lower for k in keywords)


def _is_date(value) -> bool:
    return isinstance(value, (date, datetime))


def show_ascii_chart(rows, columns, question):
    if not rows:
        print("(No data to plot — the query returned no results)")
        return

    idx_date = next((i for i, v in enumerate(rows[0]) if _is_date(v)), None)
    idx_number = next((i for i, v in enumerate(rows[0]) if isinstance(v, (int, float))), None)
    idx_category = next((i for i, v in enumerate(rows[0]) if isinstance(v, str)), None)

    if idx_number is None:
        print("(No numeric column to plot)")
        return

    pltxt.clear_figure()

    if idx_date is not None and idx_category is not None:
        categories = sorted(set(row[idx_category] for row in rows))
        unique_dates = sorted(set(row[idx_date] for row in rows))
        date_labels = [str(d) for d in unique_dates]
        positions = list(range(len(unique_dates)))

        for cat in categories:
            cat_values = []
            for d in unique_dates:
                found = next(
                    (row[idx_number] for row in rows
                     if row[idx_date] == d and row[idx_category] == cat),
                    0,
                )
                cat_values.append(found)
            pltxt.plot(positions, cat_values, label=str(cat), marker="braille")

        pltxt.xticks(positions, date_labels)

    elif idx_date is not None:
        sorted_rows = sorted(rows[:15], key=lambda r: r[idx_date])
        labels = [str(row[idx_date]) for row in sorted_rows]
        values = [row[idx_number] for row in sorted_rows]
        positions = list(range(len(labels)))
        pltxt.plot(positions, values, marker="braille")
        pltxt.xticks(positions, labels)

    else:
        chart_rows = rows[:15]
        labels = [str(row[idx_category]) for row in chart_rows]
        values = [row[idx_number] for row in chart_rows]
        pltxt.bar(labels, values, orientation="horizontal")

    pltxt.title(question)
    pltxt.plot_size(80, 20)
    pltxt.show()
def wants_dashboard(question: str) -> bool:
    return "dashboard" in question.lower()


def show_dashboard(rows, columns, question):
    """Unlike show_ascii_chart (a single chart), this draws ONE chart per
    numeric column in the result — useful when the user asks for a general
    overview ('dashboard') instead of a single metric. How many charts to
    draw is decided deterministically (Python, based on the shape of the
    data), never delegated to the LLM."""
    if not rows:
        print("(No data to build a dashboard from)")
        return

    category_idx = next((i for i, v in enumerate(rows[0]) if isinstance(v, str)), None)
    numeric_indices = [i for i, v in enumerate(rows[0]) if isinstance(v, (int, float))]

    if category_idx is None or not numeric_indices:
        print("(No suitable columns for a dashboard — need at least one text "
              "column and one numeric column)")
        return

    print(f"\n📊 Dashboard: {len(numeric_indices)} chart(s), "
          f"category column: '{columns[category_idx]}'\n")

    for num_idx in numeric_indices:
        pltxt.clear_figure()
        sorted_rows = sorted(rows, key=lambda r: (r[num_idx] or 0), reverse=True)[:15]
        labels = [str(r[category_idx]) for r in sorted_rows]
        values = [r[num_idx] or 0 for r in sorted_rows]
        pltxt.bar(labels, values, orientation="horizontal")
        pltxt.title(f"{columns[num_idx]}")
        pltxt.plot_size(80, 16)
        pltxt.show()
        print()