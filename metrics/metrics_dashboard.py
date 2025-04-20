# metrics_dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional, TypedDict

from langsmith import Client

logger = logging.getLogger("metrics_dashboard")
logger.setLevel(logging.INFO)

DEFAULT_RANGE_DAYS = 7


class RunsData(TypedDict):
    total_runs: int
    run_types: Dict[str, int]
    components: Dict[str, int]
    latencies: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    success_rate: float
    timestamps: List[Dict[str, Any]]
    prompt_tokens: List[Dict[str, Any]]
    completion_tokens: List[Dict[str, Any]]
    total_tokens: List[Dict[str, Any]]
    costs: List[Dict[str, Any]]


# --------------------------------------------------------------------------- #
# Top‑level renderer
# --------------------------------------------------------------------------- #
def render_metrics_dashboard() -> None:
    st.title("LangSmith Metrics Dashboard")

    if not st.session_state.get("langsmith_enabled", False):
        st.warning("LangSmith tracking disabled. Enable it in Settings → LangSmith.")
        return

    client = _get_cached_client()
    if not client:
        st.error("Invalid or missing LangSmith API key.")
        return

    col_l, col_r = st.columns(2)
    with col_l:
        days_back = st.slider("Time range (days)", 1, 30, DEFAULT_RANGE_DAYS)
    with col_r:
        project_name = st.text_input(
            "Project name", st.session_state.get("langsmith_project", "nav-assist")
        )

    # Manual refresh button
    if st.button("Refresh ↻"):
        st.cache_data.clear()

    start_date = datetime.now() - timedelta(days=days_back)

    with st.spinner("Loading runs…"):
        runs = _load_runs(client, project_name, start_date, datetime.now())
    if not runs:
        st.info("No runs found in this period.")
        return

    data = _process_runs_data(runs)
    tabs = st.tabs(
        ["Overview", "Component Performance", "Latency", "Prompt / Tokens"]
    )
    with tabs[0]:
        _render_overview_metrics(data)
    with tabs[1]:
        _render_component_metrics(data)
    with tabs[2]:
        _render_latency_metrics(data)
    with tabs[3]:
        _render_prompt_metrics(data, client)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _load_runs(
    client: Client, project: str, start: datetime, end: datetime
) -> List[Any]:
    try:
        return list(
            client.list_runs(
                project_name=project,
                start_time=start,
                end_time=end,
                limit=500,
            )
        )
    except Exception as exc:
        logger.error("LangSmith API error: %s", exc)
        return []


def _get_cached_client() -> Optional[Client]:
    if "langsmith_client" in st.session_state:
        return st.session_state.langsmith_client
    key = st.session_state.get("langsmith_api_key")
    if not key:
        return None
    try:
        client = Client(api_key=key)
        st.session_state.langsmith_client = client
        return client
    except Exception as exc:
        logger.error("LangSmith client init failed: %s", exc)
        return None


def _process_runs_data(runs) -> RunsData:
    data: RunsData = {
        "total_runs": len(runs),
        "run_types": {},
        "components": {},
        "latencies": [],
        "errors": [],
        "success_rate": 0.0,
        "timestamps": [],
        "prompt_tokens": [],
        "completion_tokens": [],
        "total_tokens": [],
        "costs": [],
    }

    successes = 0
    for r in runs:
        status = getattr(r, "status", "")
        if status == "success":
            successes += 1

        rtype = getattr(r, "name", "unknown")
        data["run_types"][rtype] = data["run_types"].get(rtype, 0) + 1

        comp = getattr(r, "metadata", {}).get("component", "unknown")
        data["components"][comp] = data["components"].get(comp, 0) + 1

        lat = getattr(r, "latency", None)
        if lat is not None:
            data["latencies"].append({"latency": lat, "component": comp})

        if err := getattr(r, "error", None):
            data["errors"].append({"error": str(err), "component": comp})

        usage = getattr(r, "usage", None)
        if usage:
            ts = getattr(r, "start_time", None)
            for name in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
                val = getattr(usage, name, None)
                if val is not None:
                    bucket = "costs" if name == "cost" else name
                    data[bucket].append({"value": val, "timestamp": ts})

        ts = getattr(r, "start_time", None)
        if ts:
            data["timestamps"].append(ts)

    if data["total_runs"]:
        data["success_rate"] = successes / data["total_runs"] * 100
    return data


# --------------------------------------------------------------------------- #
# UI renderers
# --------------------------------------------------------------------------- #
def _render_overview_metrics(d: RunsData) -> None:
    st.header("Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total runs", d["total_runs"])
    c2.metric("Success rate", f"{d['success_rate']:.1f}%")
    avg_lat = (
        sum(item["latency"] for item in d["latencies"]) / len(d["latencies"])
        if d["latencies"]
        else 0
    )
    c3.metric("Avg. latency", f"{avg_lat:.2f}s")

    # Run type pie
    if d["run_types"]:
        st.subheader("Run types")
        fig, ax = plt.subplots()
        ax.pie(d["run_types"].values(), labels=d["run_types"].keys(), autopct="%1.1f%%")
        st.pyplot(fig)
        plt.close(fig)

    # Errors
    if d["errors"]:
        st.subheader("Errors")
        err_df = (
            pd.DataFrame(d["errors"])
            .groupby("error")
            .size()
            .reset_index(name="Count")
            .sort_values("Count", ascending=False)
        )
        st.dataframe(err_df, use_container_width=True)
    else:
        st.success("No errors in this period 🚀")


def _render_component_metrics(d: RunsData) -> None:
    st.header("Component performance")
    comp_df = pd.DataFrame(
        [{"Component": k, "Runs": v} for k, v in d["components"].items()]
    ).sort_values("Runs", ascending=False)
    st.dataframe(comp_df, use_container_width=True)

    if not comp_df.empty:
        fig, ax = plt.subplots()
        ax.bar(comp_df["Component"], comp_df["Runs"])
        ax.set_ylabel("Runs")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)


def _render_latency_metrics(d: RunsData) -> None:
    st.header("Latency")
    if not d["latencies"]:
        st.info("No latency data.")
        return

    lat_vals = [l["latency"] for l in d["latencies"]]
    st.metric("Average latency", f"{sum(lat_vals)/len(lat_vals):.2f}s")
    fig, ax = plt.subplots()
    ax.hist(lat_vals, bins=20)
    ax.set_xlabel("Latency (s)")
    ax.set_ylabel("Runs")
    st.pyplot(fig)
    plt.close(fig)


def _render_prompt_metrics(d: RunsData, client: Client) -> None:
    st.header("Tokens & Cost")

    if not d["total_tokens"]:
        st.info("No token usage recorded.")
        return

    token_df = pd.DataFrame(
        {
            "Prompt": sum(t["value"] for t in d["prompt_tokens"]),
            "Completion": sum(t["value"] for t in d["completion_tokens"]),
            "Total": sum(t["value"] for t in d["total_tokens"]),
        },
        index=["Tokens"],
    )
    st.dataframe(token_df)

    if d["costs"]:
        cost = sum(c["value"] for c in d["costs"])
        st.metric("Estimated cost", f"${cost:.4f}")
