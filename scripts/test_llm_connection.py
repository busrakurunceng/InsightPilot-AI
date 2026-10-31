
import time

from app.backend.llm_client import (
    LLMClientError,
    OllamaClient,
)


def main() -> None:
    client = OllamaClient()

    print(f"Model: {client.model}")
    print(f"Endpoint: {client.base_url}")
    print("Testing local LLM connection...")

    start_time = time.perf_counter()

    try:
        response = client.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise assistant. "
                        "Follow the user's instructions exactly."
                    ),
                },
                {
                    "role": "user",
                    "content": "Reply with exactly: CONNECTION_OK",
                },
            ],
        )

    except LLMClientError as exc:
        print(f"Connection failed: {exc}")
        raise SystemExit(1) from exc

    elapsed = time.perf_counter() - start_time

    print(f"Response: {response.content}")
    print(f"Model returned: {response.model}")
    print(f"Wall time: {elapsed:.2f} seconds")

    if response.total_duration_ns is not None:
        print(
            "Ollama total duration: "
            f"{response.total_duration_ns / 1e9:.2f} seconds"
        )

    if response.eval_count is not None:
        print(f"Generated tokens: {response.eval_count}")

    if response.content.strip() != "CONNECTION_OK":
        raise SystemExit(
            "Connection succeeded, but response validation failed"
        )

    print("LLM connection test PASSED")


if __name__ == "__main__":
    main()
