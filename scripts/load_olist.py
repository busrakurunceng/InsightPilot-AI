
from pathlib import Path
import pandas as pd
from sqlalchemy import text

from app.database.connection import engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"

TABLE_FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "product_category_name_translation":
        "product_category_name_translation.csv",
}

CHUNK_SIZE = 5000

# ZIP prefixes must retain their leading zeros.
ZIP_COLUMNS = {
    "customers": ["customer_zip_code_prefix"],
    "sellers": ["seller_zip_code_prefix"],
    "geolocation": ["geolocation_zip_code_prefix"],
}
DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": [
        "shipping_limit_date",
    ],
    "order_reviews": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
}


def validate_files():
    """Check that all required CSV files exist before loading."""

    missing = [
        filename
        for filename in TABLE_FILES.values()
        if not (DATA_DIR / filename).is_file()
    ]

    if missing:
        raise FileNotFoundError(
            f"Missing CSV files in {DATA_DIR}: {missing}"
        )


def load_table(connection, table_name, filename):
    """Load a CSV file into its existing PostgreSQL table."""

    csv_path = DATA_DIR / filename

    dtype_overrides = {
        column: "string"
        for column in ZIP_COLUMNS.get(table_name, [])
    }

    total_rows = 0

    print(f"\nLoading {table_name}...")

    for chunk in pd.read_csv(
        csv_path,
        chunksize=CHUNK_SIZE,
        dtype=dtype_overrides,
        encoding="utf-8",
    ):
                # Convert CSV date strings into proper datetime values.
        for column in DATE_COLUMNS.get(table_name, []):
            chunk[column] = pd.to_datetime(
                chunk[column],
                format="%Y-%m-%d %H:%M:%S",
                errors="raise",
            )
        # CSV empty fields are loaded as SQL NULL.
        chunk.to_sql(
            name=table_name,
            con=connection,
            schema="public",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=500,
        )

        total_rows += len(chunk)

        print(f"  Loaded {total_rows:,} rows", end="\r")

    database_rows = connection.execute(
        text(f'SELECT COUNT(*) FROM public."{table_name}"')
    ).scalar_one()

    if database_rows != total_rows:
        raise ValueError(
            f"{table_name}: CSV rows={total_rows}, "
            f"database rows={database_rows}"
        )

    print(
        f"  {table_name}: {total_rows:,} rows verified"
    )

    return total_rows


def main():
    validate_files()

    print("=" * 55)
    print("InsightPilot AI - Olist Data Loader")
    print("=" * 55)

    # Each table is loaded in its own transaction.
    # A failed table load is rolled back.
    for table_name, filename in TABLE_FILES.items():
        with engine.begin() as connection:
            existing_rows = connection.execute(
                text(f'SELECT COUNT(*) FROM public."{table_name}"')
            ).scalar_one()

            if existing_rows > 0:
                print(
                    f"Skipping {table_name}: "
                    f"{existing_rows:,} rows already exist."
                )
                continue

            load_table(connection, table_name, filename)

    print("\nAll 9 tables loaded successfully!")


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print("\n" + "=" * 60)
        print("DATA LOADING ERROR")
        print("=" * 60)

        print("Error type:", type(error).__name__)

        current_error = error
        level = 0

        while current_error is not None and level < 5:
            print(f"\nError level {level}:")
            print("Type:", type(current_error).__name__)

            message = str(current_error)

            # Avoid printing the enormous SQL statement.
            if "Execution failed on sql" in message:
                print("SQL execution failed; checking underlying cause.")
            else:
                print("Message:", message[:1500])

            current_error = (
                getattr(current_error, "__cause__", None)
                or getattr(current_error, "__context__", None)
            )

            level += 1
