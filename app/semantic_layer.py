"""Loads the semantic layer (tables + rules + examples) from the YAML files and
turns it into the text that gets injected into the LLM prompt.

Deliberately separated from the application code: someone who knows the business
but does not program can edit the .yaml files in semantic_layer/ without
touching a single line of Python.
"""
from pathlib import Path
import yaml

SEMANTIC_LAYER_DIR = Path(__file__).resolve().parent.parent / "semantic_layer"


def _load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _table_to_text(table: dict) -> str:
    if table.get("status") == "PENDING_MODELING":
        return ""  # placeholder tables are not sent to the LLM yet

    lines = [f"Table: {table['table']}", table.get("description", "").strip(), ""]
    if table.get("status") == "PENDING_CONFIRMATION":
        lines.append("⚠ SCHEMA PENDING CONFIRMATION AGAINST THE REAL DATABASE.")

    for col_name, info in (table.get("columns") or {}).items():
        nullable = " (nullable)" if info.get("nullable") else ""
        lines.append(f"- {col_name} ({info.get('type', '?')}){nullable}: {info.get('meaning', '').strip()}")
        for rule in info.get("rules", []):
            lines.append(f"  · {rule.strip()}")

    for rule in table.get("business_rules_join", []):
        lines.append(f"- {rule.strip()}")

    return "\n".join(lines)


def build_schema() -> str:
    tables_dir = SEMANTIC_LAYER_DIR / "tables"
    blocks = []
    for file in sorted(tables_dir.glob("*.yaml")):
        if file.name.startswith("_"):
            continue  # control files (e.g. _aggregated_tables.yaml), not a table
        table = _load_yaml(file)
        text = _table_to_text(table)
        if text:
            blocks.append(text)

    rules = _load_yaml(SEMANTIC_LAYER_DIR / "business_rules.yaml")
    blocks.append("General business rules (apply to all tables):")
    for section, content in rules.items():
        blocks.append(f"\n[{section}]")
        if isinstance(content, dict):
            for k, v in content.items():
                blocks.append(f"- {k}: {v.strip() if isinstance(v, str) else v}")
        else:
            for item in content:
                blocks.append(f"- {item.strip() if isinstance(item, str) else item}")

    return "\n\n".join(blocks)


def build_examples() -> str:
    examples_dir = SEMANTIC_LAYER_DIR / "examples"
    blocks = []
    counter = 1
    for file in sorted(examples_dir.glob("*.yaml")):
        examples = _load_yaml(file) or []
        for ex in examples:
            question = ex["question"].strip()
            sql = " ".join(ex["sql"].split())  # normalize whitespace/newlines
            blocks.append(f'Example {counter}:\nQuestion: "{question}"\nSQL: {sql}')
            counter += 1
    return "\n\n".join(blocks)


# Loaded ONCE when the module is imported, not on every request
SCHEMA = build_schema()
EXAMPLES = build_examples()
