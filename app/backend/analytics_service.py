
"""Service adapter between Text-to-SQL and Business Analytics.

Module 4.2.2:
- Reuse the existing TextToSQLService.
- Convert TextToSQLResult into AnalyticsResponse.
- Profile result columns automatically.
- Preserve result metadata.
- Do not modify SQL generation or execution.
"""

from app.backend.analytics_contract import AnalyticsResponse
from app.backend.result_profiler import profile_result
from app.backend.text_to_sql_service import (
    TextToSQLResult,
    TextToSQLService,
)


def to_analytics_response(
    result: TextToSQLResult,
) -> AnalyticsResponse:
    """Convert a Text-to-SQL result into a profiled analytics response."""

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

    return AnalyticsResponse(
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


class AnalyticsService:
    """Orchestrate Text-to-SQL and analytics result conversion."""

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
        """Execute a question and return a profiled analytics result."""

        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                "Question must not be empty."
            )

        result = self.text_to_sql_service.run(
            question.strip()
        )

        return to_analytics_response(result)
