
"""Business analytics service orchestration.

Module 4.3.2:
- Execute questions through the existing TextToSQLService.
- Convert TextToSQLResult into AnalyticsResponse.
- Profile returned columns.
- Recommend a visualization based on the result structure.
- Preserve SQL and RAG metadata.

No additional LLM or database calls are introduced.
"""

from dataclasses import replace

from app.backend.analytics_contract import AnalyticsResponse
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
    """Convert a Text-to-SQL result into a complete analytics response."""

    if not isinstance(result, TextToSQLResult):
        raise TypeError(
            "Expected a TextToSQLResult instance."
        )

    columns = list(result.columns)
    rows = [dict(row) for row in result.rows]

    column_profiles = profile_result(
        columns=columns,
        rows=rows,
    )

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

    visualization = recommend_visualization(response)

    return replace(
        response,
        visualization=visualization,
    )


class AnalyticsService:
    """Run the existing Text-to-SQL pipeline and enrich its results."""

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
        """Execute a question and return a visualization-ready response."""

        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                "Question must not be empty."
            )

        result = self.text_to_sql_service.run(
            question.strip()
        )

        return to_analytics_response(result)
