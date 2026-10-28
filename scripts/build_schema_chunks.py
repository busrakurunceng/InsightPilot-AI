"""Build deterministic, human-readable retrieval chunks from schema + semantics.

Run from repository root: python scripts/build_schema_chunks.py
No database connection, embedding model, or external API is required.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def build_chunks(catalog: dict, semantics: dict) -> list[dict]:
    """Create one chunk per table, metric, and business rule."""
    if catalog.get("schema") != semantics.get("schema"):
        raise ValueError("Schema mismatch between catalog and semantics")
    table_semantics = semantics["tables"]
    chunks = []
    for table in sorted(catalog["tables"], key=lambda t: t["name"]):
        name = table["name"]
        info = table_semantics[name]
        columns = table["columns"]
        lines = [
            f"Table: {name}",
            f"Description: {info['description']}",
            f"Row grain: {info['grain']}",
            "Columns:",
        ]
        for col in columns:
            dtype = col.get("type", col.get("data_type", "unknown"))
            nullable = col.get("nullable", col.get("is_nullable", "unknown"))
            lines.append(f"- {name}.{col['name']} ({dtype}; nullable={nullable})")
        pk = table.get("primary_key", [])
        lines.append("Primary key: " + (", ".join(pk) if pk else "none declared"))
        foreign_keys = table.get("foreign_keys", [])
        if foreign_keys:
            lines.append("Physical foreign keys:")
            for fk in foreign_keys:
                remote_table = fk.get("referenced_table", fk.get("references_table"))
                local_cols = fk.get("columns", [])
                remote_cols = fk.get("referenced_columns", [])
                if local_cols and len(local_cols) == len(remote_cols) and remote_table:
                    for local, remote in zip(local_cols, remote_cols):
                        lines.append(f"- {name}.{local} -> {remote_table}.{remote}")
                else:
                    lines.append("- " + json.dumps(fk, ensure_ascii=False, sort_keys=True))
        logical = [r for r in semantics.get("logical_relationships", [])
                   if r.get("left", "").startswith(name + ".") or r.get("right", "").startswith(name + ".")]
        if logical:
            lines.append("Logical relationships (not enforced as FK):")
            for relation in logical:
                lines.append(f"- {relation['left']} = {relation['right']}: {relation.get('description', '')}")
        chunks.append({"id": f"table:{name}", "kind": "table", "source": "schema+semantics",
                       "table": name, "text": "\n".join(lines)})

    for name, definition in sorted(semantics.get("metrics", {}).items()):
        lines = [f"Business metric: {name}"]
        for key, value in definition.items():
            rendered = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
            lines.append(f"{key}: {rendered}")
        chunks.append({"id": f"metric:{name}", "kind": "metric", "source": "semantics",
                       "metric": name, "text": "\n".join(lines)})

    for name, value in sorted(semantics.get("rules", {}).items()):
        chunks.append({"id": f"rule:{name}", "kind": "rule", "source": "semantics",
                       "rule": name, "text": f"Business rule: {name}\n{value}"})
    return chunks


def main() -> None:
    catalog = json.loads((ROOT / "docs/schema_catalog.json").read_text(encoding="utf-8"))
    semantics = yaml.safe_load((ROOT / "semantic/business_semantics.yaml").read_text(encoding="utf-8"))
    chunks = build_chunks(catalog, semantics)
    ids = [c["id"] for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs")
    output = ROOT / "artifacts/schema_chunks.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = {kind: sum(c["kind"] == kind for c in chunks) for kind in ("table", "metric", "rule")}
    print(f"Wrote: {output}")
    print(f"Chunks: {len(chunks)} | Tables: {counts['table']} | Metrics: {counts['metric']} | Rules: {counts['rule']}")


if __name__ == "__main__":
    main()
