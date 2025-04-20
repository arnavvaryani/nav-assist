import os
import re
import time
import logging
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from services.langsmith_config import get_project_metrics

# ——— Logger & Session‑State Helpers —————————————————————————————
logger = logging.getLogger("nav_assist.sidebar")
logger.setLevel(logging.INFO)

def ss(key, default=None):
    return st.session_state.get(key, default)

def set_ss(key, value):
    st.session_state[key] = value

# ——— CACHED METRICS LOADER ——————————————————————————————————————
@st.cache_data
def load_metrics(project: str, days: int):
    return get_project_metrics(project, days)

# ——— VALIDATORS —————————————————————————————————————————————
def is_valid_openai_key(api_key: str) -> tuple[bool, str]:
    if not api_key:
        return False, "API key is empty"
    api_key = api_key.strip()
    if not api_key.startswith('sk-'):
        return False, "API key should start with 'sk-'"
    if len(api_key) < 30:
        return False, "API key is too short"
    if re.search(r'[^a-zA-Z0-9_\-]', api_key):
        return False, "API key contains invalid characters"
    return True, "Valid API key format"

def is_valid_langsmith_key(api_key: str) -> tuple[bool, str]:
    if not api_key:
        return False, "API key is empty"
    api_key = api_key.strip()
    if len(api_key) < 20:
        return False, "API key is too short"
    if re.search(r'[^a-zA-Z0-9_\-]', api_key):
        return False, "API key contains invalid characters"
    return True, "Valid API key format"

# ——— RESET HELPERS —————————————————————————————————————————————
def reset_analysis_state():
    set_ss('website_analyzed', False)
    set_ss('website_url', None)
    set_ss('site_data', None)

def reset_conversation():
    reset_analysis_state()
    new_id = f"conversation_{time.strftime('%Y%m%d_%H%M%S')}"
    set_ss('current_conversation_id', new_id)
    st.session_state.conversations[new_id] = {
        "title": "New Website Analysis",
        "messages": [
            {"role": "assistant", "content": "Hello! I'm your Nav Assist. Please enter a website URL to get started."}
        ],
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    set_ss('messages', st.session_state.conversations[new_id]["messages"])
    set_ss('agent_result', None)

# ——— MAIN TAB ————————————————————————————————————————————————
def render_main_tab():
    st.subheader("API Key Status")
    # OpenAI key
    if ss('api_key_set', False) and ss('api_key'):
        valid, msg = is_valid_openai_key(ss('api_key'))
        if valid:
            st.success("OpenAI API key loaded successfully")
        else:
            st.error(f"Stored OpenAI key invalid: {msg}")
            set_ss('api_key_set', False)
    if not ss('api_key_set', False):
        st.error("Valid OpenAI API key not found")
        st.info("Add a valid OpenAI API key below")
        with st.form("openai_key_form"):
            key = st.text_input(
                "Enter OpenAI API Key",
                type="password",
                help="Your key should start with 'sk-'"
            )
            if st.form_submit_button("Save API Key"):
                valid, msg = is_valid_openai_key(key)
                if valid:
                    clean = key.strip()
                    set_ss('api_key', clean)
                    set_ss('api_key_set', True)
                    os.environ["OPENAI_API_KEY"] = clean
                    st.success("OpenAI API key saved!")
                    st.rerun()
                else:
                    st.error(f"Invalid API key: {msg}")

    # LangSmith key
    st.subheader("LangSmith Metrics")
    if ss('langsmith_enabled', False):
        st.success("LangSmith tracking enabled")
    else:
        st.warning("LangSmith tracking disabled")
        with st.form("langsmith_key_form"):
            key = st.text_input(
                "Enter LangSmith API Key",
                type="password",
                help="Enable tracking of prompt metrics"
            )
            proj = st.text_input(
                "Project Name",
                value=ss('langsmith_project', 'nav-assist'),
                help="LangSmith project name"
            )
            if st.form_submit_button("Enable LangSmith"):
                valid, msg = is_valid_langsmith_key(key)
                if valid:
                    clean = key.strip()
                    set_ss('langsmith_api_key', clean)
                    set_ss('langsmith_enabled', True)
                    set_ss('langsmith_project', proj)
                    os.environ["LANGSMITH_API_KEY"] = clean
                    os.environ["LANGSMITH_PROJECT"] = proj
                    st.success("LangSmith tracking enabled!")
                    st.rerun()
                else:
                    st.error(f"Invalid LangSmith API key: {msg}")

    # Current website info
    if ss('website_analyzed', False) and ss('site_data'):
        st.subheader("Current Website")
        st.write(f"**Analyzing:** {ss('site_data').get('title','this website')}")
        st.write(f"**URL:** {ss('website_url')}")

    # Conversation history
    st.subheader("Analyses History")
    if st.button("New Website Analysis", key="new_analysis"):
        reset_conversation()
        st.rerun()

    options = []
    for conv_id, data in reversed(list(st.session_state.conversations.items())):
        title = data['title']
        ts = data.get('timestamp')
        if ts:
            try:
                dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                title = f"{title} ({dt.strftime('%b %d')})"
            except:
                pass
        options.append((conv_id, title))

    if options:
        ids, labels = zip(*options)
        sel = st.selectbox(
            "Previous analyses",
            options=ids,
            format_func=lambda x: dict(options)[x]
        )
        if sel != ss('current_conversation_id'):
            set_ss('current_conversation_id', sel)
            set_ss('messages', st.session_state.conversations[sel]["messages"].copy())
            url = st.session_state.conversations[sel].get("url")
            if url:
                set_ss('website_url', url)
                if not ss('site_data'):
                    set_ss('site_data', {
                        "url": url,
                        "title": st.session_state.conversations[sel].get("title"),
                        "internal_link_count": 0,
                        "external_link_count": 0,
                        "content_sections": []
                    })
                set_ss('website_analyzed', True)
            else:
                reset_analysis_state()
            st.rerun()

    new_title = st.text_input(
        "Rename analysis",
        value=st.session_state.conversations[ss('current_conversation_id')]["title"]
    )
    if new_title and new_title != st.session_state.conversations[ss('current_conversation_id')]["title"]:
        st.session_state.conversations[ss('current_conversation_id')]["title"] = new_title

# ——— SETTINGS TAB —————————————————————————————————————————————
def render_settings_tab():
    st.subheader("Browser Settings")
    headless = st.checkbox("Headless Mode", value=ss('headless', True), help="Run in headless mode")
    set_ss('headless', headless)

    with st.expander("Advanced Options"):
        col1, col2 = st.columns(2)
        w = st.number_input("Width", 800, 3840, ss('browser_width', 1280), step=10)
        h = st.number_input("Height", 600, 2160, ss('browser_height', 800), step=10)
        set_ss('browser_width', w)
        set_ss('browser_height', h)

        wait = st.slider("Page Load Wait (s)", 1, 30, ss('wait_time', 10))
        set_ss('wait_time', wait)

        depth = st.slider("Max Crawl Depth", 1, 5, ss('max_depth', 3))
        set_ss('max_depth', depth)

        rpm = st.slider("Requests/Minute", 10, 120, ss('requests_per_minute', 30))
        set_ss('requests_per_minute', rpm)

        pages = st.slider("Max Pages", 10, 200, ss('max_pages', 50))
        set_ss('max_pages', pages)

        st.info("Higher values will increase crawl time.")

    st.subheader("API Settings")
    model = st.selectbox(
        "OpenAI Model",
        ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
        index=["gpt-4o", "gpt-4", "gpt-3.5-turbo"].index(ss('model_name', "gpt-4o"))
    )
    set_ss('model_name', model)

    if ss('langsmith_enabled', False):
        st.subheader("LangSmith Settings")
        proj = st.text_input(
            "Project Name",
            value=ss('langsmith_project', 'nav-assist'),
            help="Group metrics under this project"
        )
        if proj != ss('langsmith_project'):
            set_ss('langsmith_project', proj)
            os.environ["LANGSMITH_PROJECT"] = proj
            st.success(f"LangSmith project set to {proj}")

        trace = st.checkbox("Detailed Tracing", ss('detailed_tracing', True))
        set_ss('detailed_tracing', trace)

    st.subheader("Debugging")
    if st.button("Check OpenAI Connection"):
        api = ss('api_key') or os.getenv("OPENAI_API_KEY")
        if not api:
            st.error("No API key found")
        else:
            os.environ["OPENAI_API_KEY"] = api
            from langchain_openai import ChatOpenAI
            try:
                ChatOpenAI(model="gpt-3.5-turbo", temperature=0).invoke("Hello")
                st.success("✅ OpenAI API connection successful!")
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")

    if ss('langsmith_enabled', False) and st.button("Check LangSmith Connection"):
        key = ss('langsmith_api_key') or os.getenv("LANGSMITH_API_KEY")
        if not key:
            st.error("No LangSmith API key found")
        else:
            os.environ["LANGSMITH_API_KEY"] = key
            from langsmith import Client
            try:
                Client(api_key=key).list_projects()
                st.success("✅ LangSmith connection successful!")
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")

# ——— METRICS TAB ——————————————————————————————————————————————
def render_metrics_tab():
    st.subheader("Website Analysis Metrics")
    if not ss('langsmith_enabled', False):
        st.warning("Enable LangSmith in Settings to view metrics")
        if st.button("Go to Settings"):
            st.experimental_set_query_params(tab="Settings")
            st.rerun()
        return

    days = st.slider("Time range (days)", 1, 30, ss('metrics_days', 7))
    set_ss('metrics_days', days)
    if st.button("Refresh Metrics"):
        st.rerun()

    with st.spinner("Loading metrics..."):
        metrics = load_metrics(ss('langsmith_project', 'nav-assist'), days)

    if 'error' in metrics:
        st.error(f"Error retrieving metrics: {metrics['error']}")
        return

    # Top‑level metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Runs", metrics.get('total_runs', 0))
    col2.metric("Success Rate", f"{metrics.get('success_rate', 0):.1f}%")
    col3.metric("Avg Latency", f"{metrics.get('avg_latency', 0):.2f}s")

    # Usage over time
    usage = metrics.get('daily_usage', [])
    if usage:
        df = pd.DataFrame(usage)
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(df['date'], df['runs'], label='Total Runs')
        ax.bar(df['date'], df['success'], label='Successful Runs', alpha=0.7)
        ax.set(xlabel='Date', ylabel='Number of Runs', title='Usage Over Time')
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("No daily usage data available")

    # Component performance
    stats = metrics.get('component_stats', {})
    if stats:
        data = []
        for comp, s in stats.items():
            data.append({
                "Component": comp.replace('_', ' ').title(),
                "Runs": s.get('count', 0),
                "Success Rate": f"{s.get('success_rate', 0):.1f}%",
                "Avg Latency": f"{s.get('avg_latency', 0):.2f}s"
            })
        dfc = pd.DataFrame(data)
        st.dataframe(dfc, use_container_width=True)

        values = [row["Runs"] for row in data]
        if sum(values) > 0:
            fig2, ax2 = plt.subplots()
            ax2.pie(values, labels=[row["Component"] for row in data], autopct='%1.1f%%')
            ax2.set_title('Component Usage')
            st.pyplot(fig2)
    else:
        st.info("No component data available")

    # Query types
    qtypes = metrics.get('queries_by_type', {})
    if qtypes:
        st.subheader("Query Types")
        mapping = {
            "information_finding": "Information Finding",
            "explanation": "Explanations",
            "how_to": "How-To Instructions",
            "contact_info": "Contact Information",
            "pricing": "Pricing Information"
        }
        qdata = [
            {"Query Type": mapping.get(k, k.replace('_',' ').title()), "Count": v}
            for k,v in qtypes.items()
        ]
        dfq = pd.DataFrame(qdata)
        c1, c2 = st.columns([1,2])
        c1.dataframe(dfq, use_container_width=True)
        fig3, ax3 = plt.subplots()
        ax3.barh(range(len(qdata)), [d["Count"] for d in qdata])
        ax3.set(
            yticks=range(len(qdata)),
            yticklabels=[d["Query Type"] for d in qdata],
            xlabel='Count',
            title='Query Types'
        )
        plt.tight_layout()
        c2.pyplot(fig3)

    # Recent activities
    recent = metrics.get('most_recent_runs', [])
    if recent:
        rows = []
        for r in recent:
            ts = r.get('timestamp')
            tstr = ts.strftime('%Y-%m-%d %H:%M') if hasattr(ts, 'strftime') else "Unknown"
            rows.append({
                "Time": tstr,
                "Type": r.get('type','Unknown'),
                "Component": r.get('component','').replace('_',' ').title(),
                "Status": "✅" if r.get('success') else "❌"
            })
        dfr = pd.DataFrame(rows)
        st.dataframe(dfr, use_container_width=True)
    else:
        st.info("No recent activity data available")

    # Error types
    errs = metrics.get('error_types', {})
    if errs:
        with st.expander("Error Types"):
            st.dataframe({"Error": list(errs.keys()), "Count": list(errs.values())})

    st.markdown("[View Full Metrics Dashboard in LangSmith](https://smith.langchain.com)")

# ——— SIDEBAR RENDERER —————————————————————————————————————————
def render_sidebar():
    with st.sidebar:
        st.title("Nav Assist")
        tabs = st.tabs(["Main", "Settings", "Metrics"])
        with tabs[0]:
            render_main_tab()
        with tabs[1]:
            render_settings_tab()
        with tabs[2]:
            render_metrics_tab()

if __name__ == "__main__":
    render_sidebar()
