
import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.search_schema import search_schema_detailed


TOP_K = 5

EVALUATION_CASES = [
    {
        "id": "Q01",
        "question": "Siparişlerin yüzde kaçı geç teslim edildi?",
        "expected": [
            "metric:late_delivery_rate",
            "table:orders",
        ],
    },
    {
        "id": "Q02",
        "question": "Teslim edilen siparişlerden ne kadar gelir elde ettik?",
        "expected": [
            "metric:delivered_product_revenue",
            "table:orders",
            "table:order_items",
        ],
    },
    {
        "id": "Q03",
        "question": "Sipariş başına ortalama gelir nedir?",
        "expected": [
            "metric:delivered_order_aov",
            "metric:delivered_product_revenue",
            "table:orders",
            "table:order_items",
        ],
    },
    {
        "id": "Q04",
        "question": "Toplam kaç sipariş var?",
        "expected": [
            "metric:total_orders",
            "table:orders",
        ],
    },
    {
        "id": "Q05",
        "question": (
            "Sipariş ve ödeme tablolarını birleştirirken "
            "nelere dikkat etmeliyiz?"
        ),
        "expected": [
            "rule:join_caveat",
            "table:orders",
            "table:order_payments",
        ],
    },
]


def calculate_metrics(expected, raw_ids, final_ids):
    """
    Raw retrieval ve final context metriklerini ayrı hesaplar.
    """
    expected_set = set(expected)
    raw_set = set(raw_ids)
    final_set = set(final_ids)

    if not expected_set:
        raise ValueError("Expected chunk listesi boş olamaz.")

    raw_hits = expected_set & raw_set
    final_hits = expected_set & final_set

    return {
        "raw_recall_at_5": round(
            len(raw_hits) / len(expected_set),
            4,
        ),
        "context_recall": round(
            len(final_hits) / len(expected_set),
            4,
        ),
        "context_precision": round(
            len(final_hits) / len(final_set),
            4,
        ) if final_set else 0.0,
        "missing": sorted(expected_set - final_set),
        "extra": sorted(final_set - expected_set),
    }


def chunk_ids(rows):
    return [row["chunk_id"] for row in rows]


def compact_raw_results(rows):
    return [
        {
            "chunk_id": row["chunk_id"],
            "similarity": round(
                float(row["similarity"]),
                4,
            ),
        }
        for row in rows
    ]


def evaluate():
    results = []

    print("\n" + "=" * 75)
    print("INSIGHTPILOT AI - SCHEMA RAG EVALUATION")
    print("=" * 75)

    for case in EVALUATION_CASES:
        print(f"\n[{case['id']}] {case['question']}")

        retrieval = search_schema_detailed(
            case["question"],
            top_k=TOP_K,
        )

        raw_results = retrieval["raw_results"]
        selected_results = retrieval["selected_results"]
        dependency_results = retrieval["dependency_results"]

        raw_ids = chunk_ids(raw_results)
        selected_ids = chunk_ids(selected_results)
        dependency_ids = chunk_ids(dependency_results)

        final_ids = list(dict.fromkeys(
            selected_ids + dependency_ids
        ))

        metrics = calculate_metrics(
            case["expected"],
            raw_ids,
            final_ids,
        )

        result = {
            "id": case["id"],
            "question": case["question"],
            "expected": case["expected"],
            "raw_results": compact_raw_results(raw_results),
            "selected_results": selected_ids,
            "dependency_results": dependency_ids,
            "final_context": final_ids,
            **metrics,
        }

        results.append(result)

        print("  Raw retrieval:")
        for row in result["raw_results"]:
            print(
                f"    {row['chunk_id']} "
                f"({row['similarity']:.4f})"
            )

        print(f"  Selected: {selected_ids}")
        print(f"  Dependencies: {dependency_ids}")
        print(f"  Final context: {final_ids}")

        print(
            f"  Raw Recall@5: "
            f"{metrics['raw_recall_at_5']:.2%}"
        )
        print(
            f"  Context Recall: "
            f"{metrics['context_recall']:.2%}"
        )
        print(
            f"  Context Precision: "
            f"{metrics['context_precision']:.2%}"
        )

        print(f"  Missing: {metrics['missing']}")
        print(f"  Extra: {metrics['extra']}")

    count = len(results)

    if not count:
        raise ValueError("Değerlendirme sorusu bulunamadı.")

    summary = {
        "total_questions": count,
        "mean_raw_recall_at_5": round(
            sum(r["raw_recall_at_5"] for r in results)
            / count,
            4,
        ),
        "mean_context_recall": round(
            sum(r["context_recall"] for r in results)
            / count,
            4,
        ),
        "mean_context_precision": round(
            sum(r["context_precision"] for r in results)
            / count,
            4,
        ),
        "full_context_recall_count": sum(
            r["context_recall"] == 1.0
            for r in results
        ),
    }

    output_dir = PROJECT_ROOT / "artifacts" / "evaluations"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = (
        output_dir / "schema_retrieval_evaluation.json"
    )
    csv_path = (
        output_dir / "schema_retrieval_evaluation.csv"
    )

    report = {
        "evaluation_date": datetime.now().isoformat(
            timespec="seconds"
        ),
        "top_k": TOP_K,
        "summary": summary,
        "results": results,
    }

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "id",
            "question",
            "raw_recall_at_5",
            "context_recall",
            "context_precision",
            "missing",
            "extra",
        ])

        for result in results:
            writer.writerow([
                result["id"],
                result["question"],
                result["raw_recall_at_5"],
                result["context_recall"],
                result["context_precision"],
                json.dumps(
                    result["missing"],
                    ensure_ascii=False,
                ),
                json.dumps(
                    result["extra"],
                    ensure_ascii=False,
                ),
            ])

    print("\n" + "=" * 75)
    print("OVERALL RESULTS")
    print("=" * 75)

    print(f"Questions: {count}")
    print(
        f"Mean Raw Recall@5: "
        f"{summary['mean_raw_recall_at_5']:.2%}"
    )
    print(
        f"Mean Context Recall: "
        f"{summary['mean_context_recall']:.2%}"
    )
    print(
        f"Mean Context Precision: "
        f"{summary['mean_context_precision']:.2%}"
    )
    print(
        f"Full Context Recall: "
        f"{summary['full_context_recall_count']}/{count}"
    )

    print(f"\nJSON report: {json_path}")
    print(f"CSV report:  {csv_path}")


if __name__ == "__main__":
    evaluate()
