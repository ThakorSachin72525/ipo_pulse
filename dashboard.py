"""Read-only Streamlit dashboard for IPO Pulse."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.config import Settings
from app.repositories.supabase_repository import SupabaseRepository


st.set_page_config(page_title="IPO Pulse", page_icon="📈", layout="wide")


@st.cache_data(ttl=300)
def load_data() -> dict[str, list[dict[str, object]]]:
    repository = SupabaseRepository.from_settings(Settings.from_env())
    return repository.get_dashboard_data()


st.title("IPO Pulse")
st.caption("GMP snapshots, prediction history, and listing accuracy")

with st.sidebar:
    st.header("Filters")
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()

try:
    data = load_data()
except Exception as error:
    st.error(f"Unable to load Supabase data: {error}")
    st.stop()

ipos = pd.DataFrame(data["ipos"])
gmp_history = pd.DataFrame(data["gmp_history"])
predictions = pd.DataFrame(data["predictions"])
results = pd.DataFrame(data["results"])

accuracy = (
    float(results["direction_accuracy"].mean() * 100)
    if not results.empty and "direction_accuracy" in results
    else None
)
mean_error = (
    float(results["percentage_error"].dropna().mean())
    if not results.empty and "percentage_error" in results and results["percentage_error"].notna().any()
    else None
)

metric_one, metric_two, metric_three, metric_four = st.columns(4)
metric_one.metric("Tracked IPOs", len(ipos))
metric_two.metric("GMP snapshots", len(gmp_history))
metric_three.metric("Predictions", len(predictions))
metric_four.metric("Direction accuracy", f"{accuracy:.1f}%" if accuracy is not None else "N/A")

st.subheader("Current IPO overview")
if ipos.empty:
    st.info("No IPO records available.")
else:
    st.dataframe(
        ipos[[column for column in ["ipo_name", "issue_price", "lot_size", "status", "listing_date", "listing_price", "source"] if column in ipos]],
        use_container_width=True,
        hide_index=True,
    )

left, right = st.columns(2)
with left:
    st.subheader("GMP history")
    if gmp_history.empty:
        st.info("No GMP snapshots available.")
    else:
        chart_data = gmp_history.pivot_table(
            index="observation_at", columns="name", values="gmp", aggfunc="last"
        )
        st.line_chart(chart_data)

with right:
    st.subheader("Prediction history")
    if predictions.empty:
        st.info("No predictions available.")
    else:
        chart_data = predictions.pivot_table(
            index="gmp_date", columns="name", values="expected_listing_price", aggfunc="last"
        )
        st.line_chart(chart_data)

st.subheader("Predicted versus actual listing price")
if results.empty:
    st.info("No listing outcomes available yet.")
else:
    display_results = results.copy()
    display_results["direction_accuracy"] = display_results["direction_accuracy"].map(
        {True: "Correct", False: "Incorrect"}
    )
    st.dataframe(display_results, use_container_width=True, hide_index=True)
    st.metric("Mean percentage error", f"{mean_error:.2f}%" if mean_error is not None else "N/A")