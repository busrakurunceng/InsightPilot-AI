
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.search_schema import search_schema


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


def calculate_metrics(expected, semantic_ids, all_ids):
    expected_set = set(expected)
    semantic_set = set(semantic_ids)
    all_set = set(all_ids)

    semantic_hits = expected_set & semantic_set
    context_hits = expected_set & all_set

    recall_at_5 = len(semantic_hits) / len(expected_set)
    context_recall = len(context_hits) / len(expected_set)

    context_precision = (
        len(context_hits) / len(all_set)
        if all_set
        else 0.0
    )

    return {
        "recall_at_5": round(recall_at_5, 4),
        "context_recall": round(context_recall, 4),
        "context_precision": round(context_precision, 4),
        "missing": sorted(expected_set - all_set),
        "extra": sorted(all_set - expected_set),
    }


def evaluate():
    results = []

    print("\n" + "=" * 75)
    print("INSIGHTPILOT AI - SCHEMA RAG RETRIEVAL EVALUATION")
    print("=" * 75)

    for case in EVALUATION_CASES:
        print(f"\n[{case['id']}] {case['question']}")

        semantic_results, dependency_results = search_schema(
            case["question"],
            top_k=5,
        )

        semantic_ids = [
            row["chunk_id"] for row in semantic_results
        ]

        dependency_ids = [
            row["chunk_id"] for row in dependency_results
        ]

        all_ids = list(dict.fromkeys(
            semantic_ids + dependency_ids
        ))

        metrics = calculate_metrics(
            case["expected"],
            semantic_ids,
            all_ids,
        )

        result = {
            "id": case["id"],
            "question": case["question"],
            "expected": case["expected"],
            "semantic_results": [
                {
                    "chunk_id": row["chunk_id"],
                    "similarity": round(
                        float(row["similarity"]), 4
                    ),
                }
                for row in semantic_results
            ],
            "dependency_results": dependency_ids,
            "all_retrieved": all_ids,
            **metrics,
        }

        results.append(result)

        print("  Semantic results:")
        for item in result["semantic_results"]:
            print(
                f"    {item['chunk_id']} "
                f"({item['similarity']:.4f})"
            )

        print("  Dependency results:")
        for chunk_id in dependency_ids:
            print(f"    {chunk_id}")

        print(
            f"  Recall@5:         "
            f"{metrics['recall_at_5']:.2%}"
        )
        print(
            f"  Context Recall:   "
            f"{metrics['context_recall']:.2%}"
        )
        print(
            f"  Context Precision:"
            f" {metrics['context_precision']:.2%}"
        )
        print(f"  Missing: {metrics['missing']}")
        print(f"  Extra:   {metrics['extra']}")

    summary = {
        "total_questions": len(results),
        "mean_recall_at_5": round(
            sum(r["recall_at_5"] for r in results)
            / len(results),
            4,
        ),
        "mean_context_recall": round(
            sum(r["context_recall"] for r in results)
            / len(results),
            4,
        ),
        "mean_context_precision": round(
            sum(r["context_precision"] for r in results)
            / len(results),
            4,
        ),
        "full_context_recall_count": sum(
            r["context_recall"] == 1.0
            for r in results
        ),
    }

    output_dir = PROJECT_ROOT / "artifacts" / "evaluations"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "schema_retrieval_evaluation.json"
    csv_path = output_dir / "schema_retrieval_evaluation.csv"

    report = {
        "evaluation_date": datetime.now().isoformat(
            timespec="seconds"
        ),
        "top_k": 5,
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
            "recall_at_5",
            "context_recall",
            "context_precision",
            "missing",
            "extra",
        ])

        for result in results:
            writer.writerow([
                result["id"],
                result["question"],
                result["recall_at_5"],
                result["context_recall"],
                result["context_precision"],
                json.dumps(
                    result["missing"], ensure_ascii=False
                ),
                json.dumps(
                    result["extra"], ensure_ascii=False
                ),
            ])

    print("\n" + "=" * 75)
    print("OVERALL RESULTS")
    print("=" * 75)

    print(f"Questions: {summary['total_questions']}")
    print(
        f"Mean Recall@5: "
        f"{summary['mean_recall_at_5']:.2%}"
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
        f"{summary['full_context_recall_count']}"
        f"/{summary['total_questions']}"
    )

    print(f"\nJSON report: {json_path}")
    print(f"CSV report:  {csv_path}")


if __name__ == "__main__":
    evaluate()
