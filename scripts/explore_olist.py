from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/raw")

csv_files = sorted(DATA_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError(
        "data/raw klasöründe CSV dosyası bulunamadı."
    )

print("=" * 65)
print("INSIGHTPILOT AI - OLIST DATA EXPLORATION")
print("=" * 65)

summary = []

for file_path in csv_files:
    print(f"\n{'=' * 65}")
    print(f"DATASET: {file_path.name}")
    print("=" * 65)

    df = pd.read_csv(file_path)

    rows, cols = df.shape
    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())

    print(f"Satır sayısı       : {rows:,}")
    print(f"Sütun sayısı       : {cols}")
    print(f"Eksik hücre sayısı : {missing:,}")
    print(f"Tekrarlanan satır  : {duplicates:,}")

    print("\nSÜTUNLAR VE VERİ TİPLERİ:")
    print(df.dtypes.to_string())

    print("\nEKSİK DEĞERLER:")
    missing_by_column = df.isna().sum()
    missing_by_column = missing_by_column[
        missing_by_column > 0
    ]

    if missing_by_column.empty:
        print("Eksik değer yok.")
    else:
        print(missing_by_column.to_string())

    print("\nİLK 3 KAYIT:")
    print(df.head(3).to_string(index=False))

    summary.append({
        "file": file_path.name,
        "rows": rows,
        "columns": cols,
        "missing_cells": missing,
        "duplicate_rows": duplicates
    })

summary_df = pd.DataFrame(summary)

print("\n" + "=" * 65)
print("GENEL VERİ SETİ ÖZETİ")
print("=" * 65)
print(summary_df.to_string(index=False))

print("\nToplam tablo:", len(summary_df))
print("Toplam kayıt:", f"{summary_df['rows'].sum():,}")