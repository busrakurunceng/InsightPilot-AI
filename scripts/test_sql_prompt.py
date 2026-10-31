
from scripts.search_schema import search_schema
from app.backend.sql_prompt_builder import build_sql_messages
from app.backend.llm_client import OllamaClient


def main():
    question = "Toplam kaç sipariş var?"

    selected_results, dependency_results = search_schema(question)

    print("Selected chunks:", [
        row["chunk_id"] for row in selected_results
    ])
    print("Dependency chunks:", [
        row["chunk_id"] for row in dependency_results
    ])

    messages = build_sql_messages(
        question,
        selected_results,
        dependency_results,
    )

    client = OllamaClient()
    response = client.chat(messages)

    print("\nGenerated SQL:")
    print(response.content)


if __name__ == "__main__":
    main()
