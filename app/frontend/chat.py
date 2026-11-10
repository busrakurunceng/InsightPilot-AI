
"""Conversational BI Streamlit page."""

import logging
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
    build_error_message,
    export_chat_history,
)
from app.frontend.components.analytics_renderer import (
    render_visualization,
)


logger = logging.getLogger(__name__)

HISTORY_KEY = "analytics_chat_history"


@st.cache_resource
def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


def render_analytics_result(
    response: AnalyticsResponse,
) -> None:
    """Render the result table, chart, insights, and SQL."""

    st.markdown("#### Analysis Results")

    st.caption(
        f"Returned rows: {response.row_count:,}"
    )

    if response.truncated:
        st.warning(
            "The result was truncated. "
            "Charts and insights may reflect only the returned rows."
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

    if response.visualization is not None and response.rows:
        st.markdown("#### Visualization")
        render_visualization(response)

    if response.insights:
        st.markdown("#### Business Insights")

        for insight in response.insights:
            st.markdown(f"- {insight}")

    with st.expander("View Generated SQL"):
        st.code(response.sql, language="sql")

    with st.expander("Technical Details"):
        st.write("Model:", response.model or "Not specified")
        st.write(
            "Selected schema chunks:",
            response.selected_chunk_ids,
        )
        st.write(
            "Dependency schema chunks:",
            response.dependency_chunk_ids,
        )


def render_message(message: ChatMessage) -> None:
    """Display one message and its saved analytics result."""

    with st.chat_message(message.role):
        if (
            message.role == "assistant"
            and message.response is None
            and message.content == build_error_message()
        ):
            st.error(message.content)
        else:
            st.markdown(message.content)

        if message.response is not None:
            render_analytics_result(message.response)


def initialize_history() -> None:
    """Create an empty history for a new Streamlit session."""

    if HISTORY_KEY not in st.session_state:
        st.session_state[HISTORY_KEY] = []


def render_sidebar(history: list[ChatMessage]) -> None:
    """Show conversation controls."""

    with st.sidebar:
        st.divider()
        st.subheader("Conversation")

        user_messages = sum(
            message.role == "user"
            for message in history
        )

        st.caption(
            f"Questions in this session: {user_messages}"
        )

        if history:
            st.download_button(
                label="Export Conversation (JSON)",
                data=export_chat_history(history),
                file_name="insightpilot_conversation.json",
                mime="application/json",
                use_container_width=True,
            )

        if st.button(
            "Clear Conversation",
            use_container_width=True,
            disabled=not history,
        ):
            st.session_state[HISTORY_KEY] = []
            st.rerun()


def main() -> None:
    st.title("Conversational BI")

    st.caption(
        "Ask questions about the Olist e-commerce dataset "
        "using natural language."
    )

    initialize_history()

    history: list[ChatMessage] = (
        st.session_state[HISTORY_KEY]
    )

    render_sidebar(history)

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

    st.session_state[HISTORY_KEY] = history

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your question..."):
            try:
                service = get_analytics_service()
                response = service.run(question)

            except Exception:
                logger.exception(
                    "Conversational analytics failed."
                )

                error_message = build_error_message()

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

    st.session_state[HISTORY_KEY] = history


main()
