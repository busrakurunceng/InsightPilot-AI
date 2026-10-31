
from app.backend.sql_generator import SQLGenerator


def main():
    generator = SQLGenerator()

    question = "Toplam kaç sipariş var?"

    print(f"\nQuestion: {question}")

    result = generator.generate(question)

    print(f"\nModel: {result.model}")

    print("\nSelected context:")
    for chunk_id in result.selected_chunk_ids:
        print(f"  - {chunk_id}")

    print("\nDependency context:")
    for chunk_id in result.dependency_chunk_ids:
        print(f"  - {chunk_id}")

    print("\nGenerated SQL:")
    print(result.sql)


if __name__ == "__main__":
    main()
