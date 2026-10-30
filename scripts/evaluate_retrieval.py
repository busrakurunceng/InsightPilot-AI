
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

BENCHMARK_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "evaluations"
    / "schema_benchmark.json"
)


def load_benchmark(path=BENCHMARK_PATH):
    with Path(path).open("r", encoding="utf-8") as file:
        benchmark = json.load(file)

    cases = benchmark["cases"]

    if not cases:
        raise ValueError("Benchmark boş olamaz.")

    ids = [case["id"] for case in cases]

    if len(ids) != len(set(ids)):
        raise ValueError("Benchmark içinde tekrarlanan soru ID'si var.")

    for case in cases:
        required = (
            "id",
            "category",
            "difficulty",
            "question",
            "expected",
        )

        for field in required:
            if field not in case:
                raise ValueError(
                    f"{case.get('id', '?')}: eksik alan {field}"
                )

        if not case["question"].strip():
            raise ValueError(f"{case['id']}: soru boş.")

        if not case["expected"]:
            raise ValueError(f"{case['id']}: expected boş.")

        if len(case["expected"]) != len(set(case["expected"])):
            raise ValueError(
                f"{case['id']}: tekrarlanan expected chunk."
            )

        if case["difficulty"] not in ("supported", "challenge"):
            raise ValueError(
                f"{case['id']}: geçersiz difficulty."
            )

    return cases


def calculate_metrics(expected, raw_ids, final_ids):
    expected_set = set(expected)
    raw_set = set(raw_ids)
    final_set = set(final_ids)

    if not expected_set:
        raise ValueError("Expected chunk listesi boş olamaz.")

    raw_hits = expected_set & raw_set
    final_hits = expected_set & final_set

    return {
        "raw_recall_at_5": round(
            len(raw_hits) / len(expected_set), 4
        ),
        "context_recall": round(
            len(final_hits) / len(expected_set), 4
        ),
        "context_precision": (
            round(len(final_hits) / len(final_set), 4)
            if final_set else 0.0
        ),
        "missing": sorted(expected_set - final_set),
        "extra": sorted(final_set - expected_set),
    }


def chunk_ids(rows):
    return [row["chunk_id"] for row in rows]


def summarize(results):
    if not results:
        raise ValueError("Özetlenecek sonuç bulunamadı.")

    count = len(results)

    return {
        "total_questions": count,
        "mean_raw_recall_at_5": round(
            sum(r["raw_recall_at_5"] for r in results) / count,
            4,
        ),
        "mean_context_recall": round(
            sum(r["context_recall"] for r in results) / count,
            4,
        ),
        "mean_context_precision": round(
            sum(r["context_precision"] for r in results) / count,
            4,
        ),
        "full_context_recall_count": sum(
            r["context_recall"] == 1.0 for r in results
        ),
        "perfect_context_count": sum(
            r["context_recall"] == 1.0
            and r["context_precision"] == 1.0
            for r in results
        ),
    }


def group_summaries(results, field):
    groups = {}

    for result in results:
        key = result[field]
        groups.setdefault(key, []).append(result)

    return {
        key: summarize(group_results)
        for key, group_results in sorted(groups.items())
    }


def evaluate():
    cases = load_benchmark()
    results = []

    print("\n" + "=" * 75)
    print("INSIGHTPILOT AI - SCHEMA RAG ROBUSTNESS EVALUATION")
    print("=" * 75)

    for case in cases:
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
            "category": case["category"],
            "difficulty": case["difficulty"],
            "question": case["question"],
            "expected": case["expected"],
            "raw_results": [
                {
                    "chunk_id": row["chunk_id"],
                    "similarity": round(
                        float(row["similarity"]), 4
                    ),
                }
                for row in raw_results
            ],
            "selected_results": selected_ids,
            "dependency_results": dependency_ids,
            "final_context": final_ids,
            **metrics,
        }

        results.append(result)

        print(f"  Raw: {raw_ids}")
        print(f"  Selected: {selected_ids}")
        print(f"  Dependencies: {dependency_ids}")
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

    summary = summarize(results)
    by_category = group_summaries(results, "category")
    by_difficulty = group_summaries(results, "difficulty")

    failures = [
        {
            "id": result["id"],
            "category": result["category"],
            "difficulty": result["difficulty"],
            "question": result["question"],
            "missing": result["missing"],
            "extra": result["extra"],
        }
        for result in results
        if result["missing"] or result["extra"]
    ]

    report = {
        "evaluation_date": datetime.now().isoformat(
            timespec="seconds"
        ),
        "benchmark_version": 1,
        "top_k": TOP_K,
        "summary": summary,
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "failures": failures,
        "results": results,
    }

    output_dir = PROJECT_ROOT / "artifacts" / "evaluations"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "schema_robustness_evaluation.json"
    csv_path = output_dir / "schema_robustness_evaluation.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with csv_path.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "id",
            "category",
            "difficulty",
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
                result["category"],
                result["difficulty"],
                result["question"],
                result["raw_recall_at_5"],
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
        f"Perfect Context: "
        f"{summary['perfect_context_count']}"
        f"/{summary['total_questions']}"
    )

    print("\nCATEGORY RESULTS")
    for category, values in by_category.items():
        print(
            f"  {category}: "
            f"recall={values['mean_context_recall']:.2%}, "
            f"precision={values['mean_context_precision']:.2%}"
        )

    print("\nDIFFICULTY RESULTS")
    for difficulty, values in by_difficulty.items():
        print(
            f"  {difficulty}: "
            f"recall={values['mean_context_recall']:.2%}, "
            f"precision={values['mean_context_precision']:.2%}"
        )

    print(f"\nCases with missing or extra chunks: {len(failures)}")
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")


if __name__ == "__main__":
    evaluate()
