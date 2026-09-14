# nl-to-sql-analytics

A prototype that lets you query analytics data in plain language — no SQL required —
backed by a local or self-hosted LLM, ClickHouse, and a semantic layer built from scratch
through iterative, evidence-based testing rather than guesswork.

> Built with the help of Claude Code. This README focuses on the engineering decisions and
> the failure modes discovered along the way — the parts that don't show up in a demo.

## What it does

```
"How many searches had a fallback in deployment_a last week?"
        ↓
LLM generates SQL from the question + a semantic layer (schema, business rules, examples)
        ↓
Deterministic Python layer validates, runs it against ClickHouse, and computes any
aggregate stats — the LLM never does arithmetic on the result
        ↓
Answer in plain text, plus an ASCII chart or multi-chart dashboard when the question
implies one (decided by the shape of the data, not by the model)
```

## Why this design

Most "chat with your data" demos hide a fragile assumption: that a language model can
reliably turn a business question into correct SQL on the first try, every time. It can't —
not consistently, not even with a well-written prompt. This project treats that as a given,
not a bug to eventually fix, and designs around it:

- **The LLM only ever does one thing: generate SQL (or narrate a result).** It never
  calculates percentages, medians, or comparisons itself — those are computed in Python and
  handed to it as already-verified numbers. This single decision eliminates an entire class
  of hallucinated statistics.
- **The semantic layer is data, not code.** Table definitions, business rules, and few-shot
  examples live in YAML (`semantic_layer/`), not hardcoded in Python strings. Anyone who
  understands the business — not necessarily the codebase — can fix a wrong rule.
- **Every discovered failure becomes a regression test.** `tests/test_known_queries.py` is a
  running log of real failures (wrong column names, wrong JOIN logic, ignored instructions)
  turned into automated checks, so a later change to the semantic layer can't silently
  reintroduce a bug that was already fixed once.

## What a semantic layer entry looks like

Each table gets a YAML file describing not just its columns, but the business logic a raw
schema can't express — the part that usually lives in someone's head or a Slack thread.
Example (using a generic e-commerce schema, not the actual data model):

```yaml
status_code:
  type: Int32
  meaning: "Result status of the operation."
  rules:
    - "status_code = 1  -> operation succeeded on the first attempt"
    - "status_code = 0  -> operation failed, no retry was attempted"
    - >
      status_code = -1 -> this row represents a VOIDED attempt: the operation originally
      failed, and a SEPARATE row (with a different source) holds the retry's real result.
      This is not an in-place correction — it's two distinct rows.
    - >
      IMPORTANT: when grouping by source for any rate calculation, EXCLUDE status_code = -1
      by default — its source reflects where the operation failed, not where it succeeded.
```

This kind of rule is exactly what a schema's `DESCRIBE TABLE` output can never tell you —
and exactly what a small LLM gets wrong most often if it isn't made explicit.

## A concrete example of the debugging process

Early on, a rule like the one above was correctly written in the schema — and the model
still generated wrong SQL for it, repeatedly, with the exact same question. The cause wasn't
a missing rule; it was **position within the prompt**. With a small model (3B parameters),
examples placed early in a long prompt were effectively ignored — a measurable recency bias,
not a one-off fluke.

The fix: a dedicated file, `semantic_layer/examples/zz_priority_examples.yaml`, which the
loader (`app/semantic_layer.py`) always appends last — closest to the actual question, where
a small model pays the most attention. Any example that fails twice with an identical
question moves there. This is documented as a standing convention, not a one-time patch.

## Architecture

```
app/
  cli.py               # entry point (terminal REPL)
  llm_service.py        # builds prompts, calls the LLM, composes the final answer
  semantic_layer.py       # loads and assembles semantic_layer/*.yaml into prompt text
  db_connection.py         # isolated ClickHouse connection (swappable for a pool later)
  sql_guard.py               # blocks destructive SQL, enforces explicit LIMIT values
  analysis.py                  # deterministic stats (mean/median/p90/MRR) over large results
  visualization.py                # ASCII charts + auto multi-chart dashboards

semantic_layer/
  tables/*.yaml          # one file per table: columns, types, business rules
  examples/*.yaml          # few-shot examples, grouped by topic
  business_rules.yaml        # cross-table rules (JOIN patterns, metric formulas)

tests/
  test_semantic_layer.py   # fast, no network — validates the YAML loads correctly
  test_known_queries.py      # regression suite against the real LLM
```

## Key engineering decisions, in short

| Decision | Why |
|---|---|
| Semantic layer in YAML, not Python | Editable by non-engineers; versionable independently of app logic |
| LLM never computes statistics | Removes the most common source of confidently-wrong numbers |
| Chart/dashboard choice is deterministic | The model decides *what* SQL to run; Python decides *how* to display it |
| A `LIMIT N` requested in plain language is enforced in code | Small models frequently ignore explicit numeric constraints in the prompt |
| Regression tests capture real, previously-seen failures | Prevents silent reintroduction of fixed bugs as the schema grows |

## What's still rough (on purpose — this is a prototype)

- Model choice matters more than expected: a larger model fixed some failure classes
  (respecting `LIMIT`, avoiding `IN` instead of `LIKE`) but introduced others (inventing
  filters that were never asked for, losing context on very short follow-up questions).
  Bigger is not strictly safer — it changes *which* mistakes are likely, not whether mistakes
  happen.
- Multi-table JOINs remain the most fragile pattern; each new JOIN shape (2 tables, 3 tables,
  JOIN + date + category) needed its own explicit example before it worked reliably.
- No production-grade concurrency yet (single Ollama/vLLM connection, no connection pooling,
  no caching) — the natural next step if this were to serve more than one user at a time.

## Running it locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your own ClickHouse + LLM endpoint
python3 -m app.cli
```

Works against a local Ollama model out of the box; swapping to a self-hosted vLLM endpoint
(or any OpenAI-compatible API) is a two-line change in `.env` — no code changes required.

## Tests

```bash
pytest tests/test_semantic_layer.py -v   # fast, no LLM call
pytest tests/test_known_queries.py -v      # slower, hits the real model
```
