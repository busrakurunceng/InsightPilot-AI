
"""Business analytics service orchestration.

Module 4.4.2:
- Execute questions through the existing TextToSQLService.
- Convert TextToSQLResult into AnalyticsResponse.
- Profile returned columns.
- Recommend a visualization.
- Generate deterministic business insights.
- Preserve SQL and RAG metadata.

No additional LLM or database calls are introduced.
"""

from dataclasses import replace

from app.backend.analytics_contract import AnalyticsResponse
from app.backend.business_insights import generate_insights
from app.backend.result_profiler import profile_result
from app.backend.text_to_sql_service import (
    TextToSQLResult,
    TextToSQLService,
)
from app.backend.visualization_recommender import (
    recommend_visualization,
)


def to_analytics_response(
    result: TextToSQLResult,
) -> AnalyticsResponse:
    """Convert a Text-to-SQL result into an enriched analytics response."""

    if not isinstance(result, TextToSQLResult):
        raise TypeError(
            "Expected a TextToSQLResult instance."
        )

    # Copy mutable result data to avoid modifying backend output.
    columns = list(result.columns)
    rows = [dict(row) for row in result.rows]

    # Step 1: infer data types and analytical roles.
    column_profiles = profile_result(
        columns=columns,
        rows=rows,
    )

    # Step 2: construct a valid intermediate response.
    response = AnalyticsResponse(
        question=result.question,
        sql=result.sql,
        columns=columns,
        rows=rows,
        row_count=result.row_count,
        truncated=result.truncated,
        column_profiles=column_profiles,
        model=result.model,
        selected_chunk_ids=list(result.selected_chunk_ids),
        dependency_chunk_ids=list(result.dependency_chunk_ids),
    )

    # Step 3: select the appropriate visualization.
    visualization = recommend_visualization(response)

    # Step 4: generate factual insights from returned data.
    insights = generate_insights(response)

    # Step 5: return a complete, immutable analytics response.
    return replace(
        response,
        visualization=visualization,
        insights=insights,
    )


class AnalyticsService:
    """Run the Text-to-SQL pipeline and enrich its results."""

    def __init__(
        self,
        text_to_sql_service: TextToSQLService | None = None,
    ) -> None:
        self.text_to_sql_service = (
            text_to_sql_service
            if text_to_sql_service is not None
            else TextToSQLService()
        )

    def run(self, question: str) -> AnalyticsResponse:
        """Execute a question and return a complete analytics result."""

        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                "Question must not be empty."
            )

        result = self.text_to_sql_service.run(
            question.strip()
        )

        return to_analytics_response(result)
