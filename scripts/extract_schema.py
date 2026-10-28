"""Export PostgreSQL public schema metadata for InsightPilot AI Module 2."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
TABLES = [
    'customers', 'geolocation', 'order_items', 'order_payments',
    'order_reviews', 'orders', 'product_category_name_translation',
    'products', 'sellers',
]


def database_url():
    if os.getenv('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    return URL.create(
        'postgresql+psycopg',
        username=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'insightpilot_db'),
    )


def main():
    engine = create_engine(database_url())
    try:
        inspector = inspect(engine)
        available = set(inspector.get_table_names(schema='public'))
        missing = sorted(set(TABLES) - available)
        if missing:
            raise RuntimeError(f'Missing tables in public schema: {missing}')

        catalog = {
            'schema': 'public',
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'tables': [],
        }
        for table in TABLES:
            columns = inspector.get_columns(table, schema='public')
            pk = inspector.get_pk_constraint(table, schema='public')
            fks = inspector.get_foreign_keys(table, schema='public')
            catalog['tables'].append({
                'name': table,
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': bool(col['nullable']),
                        'default': str(col['default']) if col.get('default') is not None else None,
                    }
                    for col in columns
                ],
                'primary_key': pk.get('constrained_columns') or [],
                'foreign_keys': [
                    {
                        'columns': fk.get('constrained_columns') or [],
                        'referenced_schema': fk.get('referred_schema') or 'public',
                        'referenced_table': fk['referred_table'],
                        'referenced_columns': fk.get('referred_columns') or [],
                    }
                    for fk in fks
                ],
            })

        output = ROOT / 'docs' / 'schema_catalog.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'Wrote {output}')
        print(f'Tables: {len(catalog["tables"])}')
        print(f'Columns: {sum(len(t["columns"]) for t in catalog["tables"])}')
        print(f'Foreign keys: {sum(len(t["foreign_keys"]) for t in catalog["tables"])}')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
