"""SkyQuery web app: ask questions about US flights in plain English.

Run:
    streamlit run app.py
"""
import time

import pandas as pd
import streamlit as st

from src.agent import answer, summarize
from src.semantic import connect

st.set_page_config(page_title="SkyQuery", page_icon="✈️")

EXAMPLES = [
    "Which carrier had the best on-time percentage?",
    "Which 5 airports with at least 10,000 flights had the worst on-time percentage?",
    "Which delay cause accounts for the most delay minutes?",
    "What was Mesa Airlines' on-time percentage?",
]


def use_example(text):
    """Fill the question box and ask straight away."""
    st.session_state.question = text
    st.session_state.run = True


@st.cache_resource
def get_connection():
    """Open the read-only database once and reuse it across reruns."""
    return connect()


st.title("✈️ SkyQuery")
st.caption("Ask questions about 20.9M US domestic flights (2023–2025). Runs fully local.")

st.write("**Try an example:**")
cols = st.columns(2)
for i, example in enumerate(EXAMPLES):
    cols[i % 2].button(example, on_click=use_example, args=(example,), use_container_width=True)

question = st.text_input("Your question", key="question",
                         placeholder="Which carrier had the best on-time percentage?")
asked = st.button("Ask", type="primary")
run_example = st.session_state.pop("run", False)

if (asked or run_example) and question:
    start = time.time()
    with st.spinner("Thinking..."):
        con = get_connection().cursor()  # a fresh cursor for this request
        result = answer(question, con, verbose=False)
        summary = summarize(question, result) if result["ok"] else None
    elapsed = time.time() - start

    if result["ok"]:
        st.write(summary)
        st.dataframe(pd.DataFrame(result["rows"], columns=result["columns"]), hide_index=True)
        if result["truncated"]:
            st.caption("Showing the first 1,000 rows.")
    else:
        st.error(f"Sorry, I couldn't answer that after {result['attempts']} attempts.")

    attempts = "1 attempt" if result["attempts"] == 1 else f"{result['attempts']} attempts"
    st.caption(f"{attempts} · {elapsed:.1f}s")

    with st.expander("Show SQL"):
        st.code(result["sql"], language="sql", wrap_lines=True)
        if not result["ok"]:
            st.caption(f"Last error: {result['error']}")