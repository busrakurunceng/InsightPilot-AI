
"""Conversational BI Streamlit page.

Module 4.5.1:
- Accept natural-language analytics questions.
- Call AnalyticsService.
- Display SQL results and deterministic insights.
- Maintain chat history in Streamlit session state.
- Handle backend errors without crashing the page.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.backend.analytics_contract import AnalyticsResponse
from app.backend.analytics_service import AnalyticsService
from app.frontend.chat_state import (
    ChatMessage,
    add_assistant_message,
    add_user_message,
)


@st.cache_resource
def get_analytics_service() -> AnalyticsService:
    """Create one reusable analytics service per cache lifecycle."""

    return AnalyticsService()


def render_analytics_result(response: AnalyticsResponse) -> None:
    """Render analytics results without executing another SQL query."""

    st.markdown("#### Analysis Results")

    st.caption(
        f"Returned rows: {response.row_count}"
    )

    if response.truncated:
        st.warning(
            "The result is truncated. "
            "Only a subset of rows is displayed."
        )

    if response.rows:
        dataframe = pd.DataFrame(
            response.rows,
            columns=response.columns,
        )

        st.dataframe(
            dataframe,
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("The query returned no rows.")

    if response.visualization is not None:
        spec = response.visualization

        st.caption(
            f"Recommended visualization: {spec.chart_type}"
        )

    if response.insights:
        st.markdown("#### Business Insights")

        for insight in response.insights:
            st.markdown(f"- {insight}")

    with st.expander("View Generated SQL"):
        st.code(
            response.sql,
            language="sql",
        )

    with st.expander("Technical Details"):
        st.write(
            "Model:",
            response.model or "Not specified",
        )

        st.write(
            "Selected schema chunks:",
            response.selected_chunk_ids,
        )

        st.write(
            "Dependency schema chunks:",
            response.dependency_chunk_ids,
        )


def render_message(message: ChatMessage) -> None:
    """Display one saved conversation message."""

    with st.chat_message(message.role):
        st.markdown(message.content)

        if message.response is not None:
            render_analytics_result(message.response)


def main() -> None:
    """Render the Conversational BI interface."""

    st.title("Conversational BI")

    st.caption(
        "Ask questions about the Olist e-commerce dataset "
        "using natural language."
    )

    if "analytics_chat_history" not in st.session_state:
        st.session_state.analytics_chat_history = []

    history: list[ChatMessage] = (
        st.session_state.analytics_chat_history
    )

    with st.sidebar:
        st.divider()
        st.subheader("Conversation")

        if st.button(
            "Clear Conversation",
            use_container_width=True,
        ):
            st.session_state.analytics_chat_history = []
            st.rerun()

    if not history:
        st.info(
            "Ask your first analytics question to get started."
        )

        st.markdown(
            """
            **Example questions**

            - How many orders are in the database?
            - Show the number of orders by customer state.
            - What is the monthly order trend?
            """
        )

    for message in history:
        render_message(message)

    question = st.chat_input(
        "Ask a question about your data..."
    )

    if not question or not question.strip():
        return

    question = question.strip()

    history = add_user_message(
        history,
        question,
    )

    st.session_state.analytics_chat_history = history

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your question..."):
            try:
                service = get_analytics_service()

                response = service.run(question)

            except Exception:
                error_message = (
                    "The analysis could not be completed. "
                    "Check the database connection, "
                    "local model availability, and application logs."
                )

                st.error(error_message)

                history = add_assistant_message(
                    history,
                    error_message,
                )

            else:
                success_message = (
                    "The analysis is complete."
                )

                st.markdown(success_message)

                render_analytics_result(response)

                history = add_assistant_message(
                    history,
                    success_message,
                    response=response,
                )

    st.session_state.analytics_chat_history = history


main()
