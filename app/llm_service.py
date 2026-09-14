"""Orchestrates the conversation with the LLM: generates SQL and composes the
final answer.

It knows nothing about ClickHouse, or Terminal/FastAPI — it only knows "given a
question and a history, produce SQL" and "given a result, write text".
"""
from openai import OpenAI
from app.config import ENV
from app.semantic_layer import SCHEMA, EXAMPLES
from app.sql_guard import strip_markdown
from app.analysis import summarize_multirow, SUMMARY_ROW_THRESHOLD

MODEL = ENV.get("LLM_MODEL", "qwen2.5-coder:3b")

llm = OpenAI(
    base_url=ENV.get("LLM_BASE_URL", "http://localhost:11434/v1"),
    api_key=ENV.get("LLM_API_KEY", "ollama"),
    timeout=60,
)


def _build_prior_context(history: list) -> str:
    if not history:
        return ""
    block = "Context from the previous conversation (last questions and their SQL):\n"
    for turn in history:
        block += f'Previous question: "{turn["question"]}"\nSQL used: {turn["sql"]}\n\n'
    block += (
        "If the new question refers implicitly to the previous one, use the prior "
        "context to understand what is being asked, taking the previous SQL as a base. "
        "VERY IMPORTANT: keep exactly the same date filters (INTERVAL), deployment_id "
        "and other conditions from the previous SQL, unless the new question explicitly "
        "indicates a change. Do NOT use values from the reference examples if they "
        "contradict the context of the previous conversation.\n\n"
    )
    return block


def generate_sql(question: str, history: list) -> str:
    prior_context = _build_prior_context(history)

    prompt = f"""You are a ClickHouse SQL expert.

{SCHEMA}

Here are examples of questions already answered correctly:
{EXAMPLES}

{prior_context}
Now generate the SQL for this new question: "{question}"

Rules:
- Reply ONLY with the SQL, no explanations, no markdown, no ```
- Always use LIMIT 100 if the query is not an aggregation (COUNT, SUM, AVG...)
- Do not use columns that are not in the schema
- Strictly follow the business rules in the schema
"""
    response = llm.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()
    return strip_markdown(sql)


def compose_answer(question: str, sql: str, rows, columns) -> str:
    if len(rows) <= SUMMARY_ROW_THRESHOLD:
        prompt = f"""The user asked: "{question}"

This SQL query was run: {sql}

Result (columns: {columns}):
{rows}

Write a clear, short answer in English for the user, based only on this data.
"""
    else:
        summary = summarize_multirow(rows, columns)
        prompt = f"""The user asked: "{question}"

A SQL query was run that returned {len(rows)} rows (too many to list them all).
Here is data ALREADY COMPUTED and verified about that result:
{summary}

Write a short answer in English explaining this computed data.
Do NOT invent or mention numbers that are not in this summary.
Explicitly mention that the result has {len(rows)} rows in total.
"""
    response = llm.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()
