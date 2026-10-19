"""Read-only Streamlit dashboard for IPO Pulse."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from app.config import Settings
from app.repositories.supabase_repository import SupabaseRepository


st.set_page_config(page_title="IPO Pulse", page_icon="📈", layout="wide")


@st.cache_data(ttl=300)
def load_data() -> dict[str, list[dict[str, object]]]:
    repository = SupabaseRepository.from_settings(Settings.from_env())
    return repository.get_dashboard_data()


st.title("IPO Pulse")
st.caption("GMP snapshots, prediction history, listing accuracy, and trial-ready analytics")


with st.sidebar:
    st.header("Filters")
    st.caption("All filters apply to the views below.")
    refresh = st.button("Refresh data", width="stretch")
    if refresh:
        st.cache_data.clear()
        st.rerun()

try:
    data = load_data()
except Exception as error:  # noqa: BLE001
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

# ---- Optional dashboard filters -------------------------------------------------
available_statuses = sorted(ipos["status"].dropna().unique().tolist()) if "status" in ipos else []
selected_statuses = st.sidebar.multiselect(
    "IPO status",
    options=available_statuses,
    default=available_statuses,
)
search_text = st.sidebar.text_input("Search IPO name").strip().lower()

minimum_gmp = None
maximum_gmp = None
if not gmp_history.empty and "gmp" in gmp_history and gmp_history["gmp"].notna().any():
    minimum_gmp, maximum_gmp = float(gmp_history["gmp"].min()), float(gmp_history["gmp"].max())
gmp_lower = st.sidebar.slider(
    "Minimum GMP",
    min_value=minimum_gmp if minimum_gmp is not None else 0.0,
    max_value=max(maximum_gmp or 1.0, 1.0),
    value=minimum_gmp if minimum_gmp is not None else 0.0,
) if minimum_gmp is not None else 0.0

filtered_ipos = ipos.copy()
if not filtered_ipos.empty:
    if selected_statuses and "status" in filtered_ipos:
        filtered_ipos = filtered_ipos[filtered_ipos["status"].isin(selected_statuses)]
    if search_text:
        name_column = "ipo_name" if "ipo_name" in filtered_ipos else filtered_ipos.columns[filtered_ipos.columns.str.contains("name", case=False)][0]
        filtered_ipos = filtered_ipos[
            filtered_ipos[name_column].fillna("").astype(str).str.lower().str.contains(search_text, regex=False)
        ]

ipo_id_set = set(filtered_ipos.get("ipo_id", pd.Series(dtype=object))) if "ipo_id" in filtered_ipos else filtered_ipos.index
filtered_gmp = gmp_history[gmp_history["ipo_id"].isin(ipo_id_set)].copy() if not gmp_history.empty and "ipo_id" in gmp_history else gmp_history.copy()
if not filtered_gmp.empty and minimum_gmp is not None:
    filtered_gmp = filtered_gmp[filtered_gmp["gmp"].fillna(0) >= gmp_lower]
filtered_predictions = predictions[predictions["ipo_id"].isin(ipo_id_set)].copy() if not predictions.empty and "ipo_id" in predictions else predictions.copy()
filtered_results = results[results["ipo_id"].isin(ipo_id_set)].copy() if not results.empty and "ipo_id" in results else results.copy()

accuracy = (
    float(filtered_results["direction_accuracy"].mean() * 100)
    if not filtered_results.empty and "direction_accuracy" in filtered_results
    else None
)
mean_error = (
    float(filtered_results["percentage_error"].dropna().mean())
    if not filtered_results.empty and "percentage_error" in filtered_results and filtered_results["percentage_error"].notna().any()
    else None
)

# ---- KPIs --------------------------------------------------------------------
metric_one, metric_two, metric_three, metric_four = st.columns(4)
metric_one.metric("Tracked IPOs shown", len(filtered_ipos))
metric_two.metric("GMP snapshots shown", len(filtered_gmp))
metric_three.metric("Predictions shown", len(filtered_predictions))

latest_observation = None
if not filtered_gmp.empty and "observation_at" in filtered_gmp:
    latest_observation = pd.to_datetime(filtered_gmp["observation_at"], errors="coerce").max()

metric_four.metric(
    "Direction accuracy",
    f"{accuracy:.1f}%" if accuracy is not None else "N/A",
)

kpi_cols = st.columns(3)
unique_ipos = len(filtered_ipos)
prediction_coverage = (
    filtered_predictions["ipo_id"].nunique() / unique_ipos * 100
    if unique_ipos and not filtered_predictions.empty
    else None
)
outcome_coverage = (
    filtered_results["ipo_id"].nunique() / unique_ipos * 100
    if unique_ipos and not filtered_results.empty
    else None
)
kpi_cols[0].metric("Prediction coverage", f"{prediction_coverage:.1f}%" if prediction_coverage is not None else "N/A")
kpi_cols[1].metric("Outcome coverage", f"{outcome_coverage:.1f}%" if outcome_coverage is not None else "N/A")
kpi_cols[2].metric("Mean percentage error", f"{mean_error:.2f}%" if mean_error is not None else "N/A")
st.caption(
    "Data freshness: "
    + (latest_observation.strftime("%Y-%m-%d %H:%M UTC") if latest_observation is not None and not pd.isna(latest_observation) else "unknown")
)

# ---- Current IPO overview ----------------------------------------------------
st.subheader("Current IPO overview")
if filtered_ipos.empty:
    st.info("No IPO records match the active filters.")
else:
    visible_columns = [column for column in ["ipo_name", "issue_price", "lot_size", "status", "listing_date", "listing_price", "source"] if column in filtered_ipos]
    st.dataframe(filtered_ipos[visible_columns], use_container_width=True, hide_index=True)

# ---- Charts -------------------------------------------------------------------
left, right = st.columns(2)
with left:
    st.subheader("GMP history")
    if filtered_gmp.empty:
        st.info("No GMP snapshots match the active filters.")
    else:
        chart_data = filtered_gmp.pivot_table(
            index="observation_at", columns="name", values="gmp", aggfunc="last"
        )
        trend = px.line(chart_data, title="GMP per IPO") if len(chart_data.columns) else None
        if trend is not None:
            st.plotly_chart(trend, use_container_width=True)
        else:
            st.info("No chartable GMP data is available.")
with right:
    st.subheader("Prediction history")
    if filtered_predictions.empty:
        st.info("No predictions match the active filters.")
    else:
        chart_data = filtered_predictions.pivot_table(
            index="gmp_date", columns="name", values="expected_listing_price", aggfunc="last"
        )
        trend = px.line(chart_data, title="Expected listing price") if len(chart_data.columns) else None
        if trend is not None:
            st.plotly_chart(trend, use_container_width=True)
        else:
            st.info("No chartable prediction data is available.")

st.subheader("Predicted versus actual listing price")
if filtered_results.empty:
    st.info("No listing outcomes are available yet.")
else:
    display_results = filtered_results.copy()
    if "direction_accuracy" in display_results:
        display_results["direction_accuracy"] = display_results["direction_accuracy"].map(
            {True: "Correct", False: "Incorrect", None: "N/A"}
        )
    scatter = px.scatter(
        display_results,
        x="predicted_listing_price",
        y="actual_listing_price",
        color="direction_accuracy" if "direction_accuracy" in display_results else None,
        hover_name="name" if "name" in display_results else None,
        title="Predicted vs actual listing price",
    )
    st.plotly_chart(scatter, use_container_width=True)
    st.dataframe(display_results, use_container_width=True, hide_index=True)
    st.metric("Mean percentage error (shown)", f"{mean_error:.2f}%" if mean_error is not None else "N/A")

# ---- Exports -------------------------------------------------------------------
with st.expander("Export filtered data"):
    st.download_button(
        "Download shown IPOs as CSV",
        data=filtered_ipos.to_csv(index=False).encode("utf-8"),
        file_name="ipo_pulse_ipos.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download shown results as CSV",
        data=filtered_results.to_csv(index=False).encode("utf-8"),
        file_name="ipo_pulse_listing_results.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download shown GMP history as CSV",
        data=filtered_gmp.to_csv(index=False).encode("utf-8"),
        file_name="ipo_pulse_gmp_history.csv",
        mime="text/csv",
    )

with st.expander("Method notes"):
    st.write(
        "IPO Pulse compares each prediction against its saved GMP before listing, "
        "then stores reconciliation results separately. GMP is a market sentiment "
        "indicator and is not a guaranteed listing price."
    )
