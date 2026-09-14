"""Terminal entry point — equivalent to the original poc.py, now built on top
of the separate modules in app/.

Usage: python3 -m app.cli
"""
from app.db_connection import run_sql
from app.llm_service import generate_sql, compose_answer
from app.sql_guard import is_sql_safe, enforce_limit_from_question
from app.visualization import wants_chart, show_ascii_chart, wants_dashboard, show_dashboard

MAX_HISTORY = 3
ROW_DISPLAY_LIMIT = 30


def main():
    history: list = []
    print("Ready. Type your question (or 'exit' to quit).\n")

    while True:
        question = input("Your question: ")
        if question.lower() in ("exit", "quit"):
            break

        print("\n-> Generating SQL...")
        sql = generate_sql(question, history)
        sql = enforce_limit_from_question(sql, question)
        print("Generated SQL:", sql)

        if not is_sql_safe(sql):
            print("⚠️ SQL blocked for safety, not executed.\n")
            continue

        try:
            print("-> Running on ClickHouse...")
            rows, columns = run_sql(sql)
        except Exception as e:
            print(f"❌ Error running the query: {e}\n")
            continue

        if wants_dashboard(question):
            show_dashboard(rows, columns, question)
        elif wants_chart(question):
            print("\n📈 Chart:")
            show_ascii_chart(rows, columns, question)
            print()

        print("-> Composing answer...")
        final_answer = compose_answer(question, sql, rows, columns)
        print("\n📊 Answer:", final_answer)

        if len(rows) <= ROW_DISPLAY_LIMIT:
            print(f"\n(Raw data — {len(rows)} rows, columns: {columns})")
            for row in rows:
                print("  ", row)
        else:
            print(f"\n(Raw data — showing {ROW_DISPLAY_LIMIT} of {len(rows)} rows, columns: {columns})")
            for row in rows[:ROW_DISPLAY_LIMIT]:
                print("  ", row)
        print()

        history.append({"question": question, "sql": sql})
        if len(history) > MAX_HISTORY:
            history.pop(0)


if __name__ == "__main__":
    main()
