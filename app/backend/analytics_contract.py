
"""Data contracts for the InsightPilot business analytics layer.

Module 4.1 defines the interface between the existing Text-to-SQL
backend, analytical processing, and future Streamlit components.
"""

from dataclasses import dataclass, field
from typing import Any, Literal


ColumnType = Literal[
    "numeric",
    "categorical",
    "datetime",
    "boolean",
    "unknown",
]

ColumnRole = Literal[
    "dimension",
    "measure",
    "unknown",
]

VisualizationType = Literal[
    "kpi",
    "table",
    "bar",
    "line",
]


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    data_type: ColumnType
    role: ColumnRole
    nullable: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Column name must not be empty.")


@dataclass(frozen=True)
class VisualizationSpec:
    chart_type: VisualizationType
    x_column: str | None = None
    y_column: str | None = None
    title: str = ""

    def __post_init__(self) -> None:
        if self.chart_type in ("bar", "line"):
            if not self.x_column or not self.y_column:
                raise ValueError(
                    "Bar and line charts require x_column and y_column."
                )

        if self.chart_type == "kpi" and not self.y_column:
            raise ValueError(
                "KPI visualization requires a value column."
            )


@dataclass(frozen=True)
class AnalyticsResponse:
    question: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool

    column_profiles: list[ColumnProfile] = field(
        default_factory=list
    )

    visualization: VisualizationSpec | None = None

    insights: list[str] = field(default_factory=list)

    model: str | None = None

    selected_chunk_ids: list[str] = field(
        default_factory=list
    )

    dependency_chunk_ids: list[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError("Question must not be empty.")

        if not self.sql.strip():
            raise ValueError("SQL must not be empty.")

        if self.row_count < 0:
            raise ValueError("Row count cannot be negative.")

        if self.row_count != len(self.rows):
            raise ValueError(
                "Row count must match the number of returned rows."
            )

        if len(self.columns) != len(set(self.columns)):
            raise ValueError("Column names must be unique.")

        expected_columns = set(self.columns)

        for row in self.rows:
            if set(row) != expected_columns:
                raise ValueError(
                    "Every result row must match the declared columns."
                )

        profile_names = [
            profile.name for profile in self.column_profiles
        ]

        if len(profile_names) != len(set(profile_names)):
            raise ValueError("Column profiles must be unique.")

        if not set(profile_names).issubset(expected_columns):
            raise ValueError(
                "Column profiles must reference result columns."
            )

        if self.visualization is not None:
            referenced_columns = (
                self.visualization.x_column,
                self.visualization.y_column,
            )

            for column in referenced_columns:
                if column is not None and column not in expected_columns:
                    raise ValueError(
                        "Visualization references an unknown column."
                    )
