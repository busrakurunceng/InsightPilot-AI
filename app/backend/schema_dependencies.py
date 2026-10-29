
from pathlib import Path
import re

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMANTICS_PATH = (
    PROJECT_ROOT / "semantic" / "business_semantics.yaml"
)

# "orders.order_id" gibi tablo.sütun ifadelerini yakalar.
COLUMN_REFERENCE = re.compile(
    r"\b([A-Za-z_]\w*)\.[A-Za-z_]\w*\b"
)


def load_semantics(path=SEMANTICS_PATH):
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def metric_dependencies(metric_name, semantics):
    """
    Bir metriğin ihtiyaç duyduğu metric ve table chunk ID'lerini bulur.
    İç içe metrik bağımlılıklarını da takip eder.
    """
    metrics = semantics["metrics"]
    known_tables = set(semantics["tables"])

    dependencies = []
    visited = set()

    def add(chunk_id):
        if chunk_id not in dependencies:
            dependencies.append(chunk_id)

    def visit(name):
        if name in visited:
            return

        if name not in metrics:
            raise ValueError(f"Bilinmeyen metrik: {name}")

        visited.add(name)
        definition = metrics[name]

        # Başka bir metriğe referans varsa önce onu çöz.
        for field in ("numerator", "denominator"):
            value = definition.get(field)

            if isinstance(value, str) and value in metrics:
                add(f"metric:{value}")
                visit(value)

        # Temel tabloyu ekle.
        base_table = definition.get("base_table")

        if base_table:
            if base_table not in known_tables:
                raise ValueError(f"Bilinmeyen tablo: {base_table}")
            add(f"table:{base_table}")

        # JOIN, filtre ve sütun ifadelerindeki tabloları bul.
        fields = (
            "expression",
            "joins",
            "status_filter",
            "date_column",
            "required_columns",
            "denominator",
        )

        for field in fields:
            value = definition.get(field)

            if value is None:
                continue

            values = value if isinstance(value, list) else [value]

            for item in values:
                if not isinstance(item, str):
                    continue

                for table_name in COLUMN_REFERENCE.findall(item):
                    if table_name in known_tables:
                        add(f"table:{table_name}")

    visit(metric_name)
    return dependencies
