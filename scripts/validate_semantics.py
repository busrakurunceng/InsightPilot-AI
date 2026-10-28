"""Validate InsightPilot business semantics against extracted PostgreSQL schema."""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUALIFIED_COLUMN = re.compile(r"\b([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\b")


def validate(catalog: dict, semantics: dict) -> list[str]:
    errors = []
    tables = {t['name']: {c['name'] for c in t['columns']} for t in catalog['tables']}
    described = semantics.get('tables', {})
    metrics = semantics.get('metrics', {})

    if catalog.get('schema') != semantics.get('schema'):
        errors.append('Schema names differ between catalog and semantics')
    for table in sorted(set(tables) - set(described)):
        errors.append(f'Missing table description: {table}')
    for table in sorted(set(described) - set(tables)):
        errors.append(f'Unknown semantic table: {table}')
    for table, definition in described.items():
        if not isinstance(definition, dict) or not definition.get('description') or not definition.get('grain'):
            errors.append(f'Missing description or grain: {table}')

    def check_column(ref: str, context: str):
        table, col = ref.split('.', 1)
        if table not in tables:
            errors.append(f'{context}: unknown table {table}')
        elif col not in tables[table]:
            errors.append(f'{context}: unknown column {ref}')

    def scan(value, context: str):
        if isinstance(value, str):
            for table, col in QUALIFIED_COLUMN.findall(value):
                check_column(f'{table}.{col}', context)
        elif isinstance(value, list):
            for i, entry in enumerate(value):
                scan(entry, f'{context}[{i}]')
        elif isinstance(value, dict):
            for key, entry in value.items():
                scan(entry, f'{context}.{key}')

    for i, relation in enumerate(semantics.get('logical_relationships', [])):
        for side in ('left', 'right'):
            ref = relation.get(side)
            if not isinstance(ref, str) or not re.fullmatch(r'[A-Za-z_]\w*\.[A-Za-z_]\w*', ref):
                errors.append(f'logical_relationships[{i}].{side}: invalid reference')
            else:
                check_column(ref, f'logical_relationships[{i}].{side}')
    for name, definition in metrics.items():
        if not isinstance(definition, dict) or not definition.get('description'):
            errors.append(f'Metric {name}: missing description')
            continue
        if 'base_table' in definition and definition['base_table'] not in tables:
            errors.append(f'Metric {name}: unknown base_table {definition["base_table"]}')
        for key in ('expression', 'joins', 'status_filter', 'date_column', 'required_columns', 'denominator'):
            scan(definition.get(key), f'metrics.{name}.{key}')
        numerator = definition.get('numerator')
        if numerator is not None and numerator not in metrics:
            errors.append(f'Metric {name}: unknown numerator metric {numerator}')
    return errors


def main():
    catalog_path = ROOT / 'docs' / 'schema_catalog.json'
    semantic_path = ROOT / 'semantic' / 'business_semantics.yaml'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    semantics = yaml.safe_load(semantic_path.read_text(encoding='utf-8'))
    errors = validate(catalog, semantics)
    print(f'Tables: {len(catalog["tables"])} | Metrics: {len(semantics["metrics"])} | Errors: {len(errors)}')
    if errors:
        for error in errors:
            print(f'ERROR: {error}')
        raise SystemExit(1)
    print('Semantic validation passed.')


if __name__ == '__main__':
    main()
