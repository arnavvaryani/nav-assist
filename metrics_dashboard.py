import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
import json
from typing import Dict, Any, List, Optional

from langsmith import Client

logger = logging.getLogger("metrics_dashboard")

def render_metrics_dashboard():
    """Render a comprehensive metrics dashboard using LangSmith data."""
    st.title("LangSmith Metrics Dashboard")
    
    # Check if LangSmith is enabled
    if not st.session_state.get('langsmith_enabled', False):
        st.warning("LangSmith metrics tracking is not enabled. Enable it in the Settings tab to view metrics.")
        
        # Add a button to directly open settings tab
        if st.button("Enable LangSmith Tracking"):
            # Can add logic to switch tabs here
            st.info("Please go to the Settings tab to enable LangSmith")
            return
        
        return
    
    try:
        # Initialize LangSmith client
        client = _initialize_langsmith_client()
        if not client:
            st.error("Failed to initialize LangSmith client. Please check your API key.")
            return
        
        # Set up date range selector
        col1, col2 = st.columns(2)
        with col1:
            days_back = st.slider("Time range (days)", min_value=1, max_value=30, value=7)
        with col2:
            project_name = st.text_input("Project name", value=st.session_state.get('langsmith_project', 'nav-assist'))
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Fetch runs
        with st.spinner("Fetching LangSmith data..."):
            runs = list(client.list_runs(
                project_name=project_name,
                start_time=start_date,
                end_time=end_date,
                limit=500  # Adjust limit as needed
            ))
            
            if not runs:
                st.info("No data found for the selected time range and project.")
                return
                
            st.success(f"Loaded {len(runs)} runs from LangSmith")
        
        # Process the runs data
        runs_data = _process_runs_data(runs)
        
        # Display dashboard tabs
        overview_tab, components_tab, latency_tab, prompts_tab = st.tabs([
            "Overview", "Component Performance", "Latency Analysis", "Prompt Analysis"
        ])
        
        # Overview Tab
        with overview_tab:
            _render_overview_metrics(runs_data)
            
        # Components Tab
        with components_tab:
            _render_component_metrics(runs_data)
            
        # Latency Tab
        with latency_tab:
            _render_latency_metrics(runs_data)
            
        # Prompts Tab
        with prompts_tab:
            _render_prompt_metrics(runs_data, client, project_name)
        
    except Exception as e:
        logger.error(f"Error rendering metrics dashboard: {str(e)}")
        st.error(f"Error rendering metrics dashboard: {str(e)}")
        
def _initialize_langsmith_client() -> Optional[Client]:
    """Initialize the LangSmith client."""
    try:
        # Get API key from session state
        api_key = st.session_state.get('langsmith_api_key')
        if not api_key:
            st.warning("LangSmith API key not found in session state.")
            return None
            
        # Initialize client
        client = Client(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Error initializing LangSmith client: {str(e)}")
        return None

def _process_runs_data(runs) -> Dict[str, Any]:
    """Process the runs data for dashboard display."""
    data = {
        "total_runs": len(runs),
        "run_types": {},
        "components": {},
        "latencies": [],
        "errors": [],
        "success_rate": 0,
        "feedback": [],
        "prompt_tokens": [],
        "completion_tokens": [],
        "total_tokens": [],
        "costs": [],
        "timestamps": []
    }
    
    successful_runs = 0
    
    for run in runs:
        # Process run status
        if hasattr(run, "status") and run.status == "success":
            successful_runs += 1
            
        # Process run type
        run_type = run.name if hasattr(run, "name") else "unknown"
        if run_type in data["run_types"]:
            data["run_types"][run_type] += 1
        else:
            data["run_types"][run_type] = 1
            
        # Process component
        component = None
        if hasattr(run, "metadata") and run.metadata:
            component = run.metadata.get("component", "unknown")
            
        if component:
            if component in data["components"]:
                data["components"][component] += 1
            else:
                data["components"][component] = 1
                
        # Process latency
        if hasattr(run, "latency") and run.latency:
            data["latencies"].append({
                "run_id": run.id,
                "type": run_type,
                "component": component,
                "latency": run.latency,
                "timestamp": run.start_time if hasattr(run, "start_time") else None
            })
            
        # Process errors
        if hasattr(run, "error") and run.error:
            data["errors"].append({
                "run_id": run.id,
                "type": run_type,
                "component": component,
                "error": str(run.error),
                "timestamp": run.start_time if hasattr(run, "start_time") else None
            })
            
        # Process feedback
        if hasattr(run, "feedback") and run.feedback:
            for feedback in run.feedback:
                data["feedback"].append({
                    "run_id": run.id,
                    "type": run_type,
                    "component": component,
                    "feedback_key": feedback.key,
                    "feedback_value": feedback.value,
                    "timestamp": feedback.created_at if hasattr(feedback, "created_at") else None
                })
                
        # Process token usage
        if hasattr(run, "usage") and run.usage:
            usage = run.usage
            if hasattr(usage, "prompt_tokens"):
                data["prompt_tokens"].append({
                    "run_id": run.id,
                    "type": run_type,
                    "component": component,
                    "tokens": usage.prompt_tokens,
                    "timestamp": run.start_time if hasattr(run, "start_time") else None
                })
                
            if hasattr(usage, "completion_tokens"):
                data["completion_tokens"].append({
                    "run_id": run.id,
                    "type": run_type,
                    "component": component,
                    "tokens": usage.completion_tokens,
                    "timestamp": run.start_time if hasattr(run, "start_time") else None
                })
                
            if hasattr(usage, "total_tokens"):
                data["total_tokens"].append({
                    "run_id": run.id,
                    "type": run_type,
                    "component": component,
                    "tokens": usage.total_tokens,
                    "timestamp": run.start_time if hasattr(run, "start_time") else None
                })
                
            if hasattr(usage, "cost"):
                data["costs"].append({
                    "run_id": run.id,
                    "type": run_type,
                    "component": component,
                    "cost": usage.cost,
                    "timestamp": run.start_time if hasattr(run, "start_time") else None
                })
                
        # Process timestamp
        if hasattr(run, "start_time") and run.start_time:
            data["timestamps"].append({
                "run_id": run.id,
                "type": run_type,
                "component": component,
                "timestamp": run.start_time
            })
            
    # Calculate success rate
    if data["total_runs"] > 0:
        data["success_rate"] = (successful_runs / data["total_runs"]) * 100
        
    return data

def _render_overview_metrics(data: Dict[str, Any]):
    """Render overview metrics section."""
    st.header("Overview Metrics")
    
    # Display key metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Runs", data["total_runs"])
    with col2:
        st.metric("Success Rate", f"{data['success_rate']:.1f}%")
    with col3:
        avg_latency = 0
        if data["latencies"]:
            latencies = [item["latency"] for item in data["latencies"]]
            avg_latency = sum(latencies) / len(latencies)
        st.metric("Avg. Latency", f"{avg_latency:.2f}s")
        
    # Display run types breakdown
    st.subheader("Run Types Distribution")
    if data["run_types"]:
        fig, ax = plt.subplots()
        labels = list(data["run_types"].keys())
        values = list(data["run_types"].values())
        ax.pie(values, labels=labels, autopct='%1.1f%%')
        ax.set_title('Run Types')
        st.pyplot(fig)
        
        # Also display as a table
        run_types_df = pd.DataFrame({
            "Type": labels,
            "Count": values,
            "Percentage": [f"{(v/sum(values))*100:.1f}%" for v in values]
        })
        st.dataframe(run_types_df)
    else:
        st.info("No run types data available")
        
    # Error summary
    st.subheader("Error Summary")
    if data["errors"]:
        error_counts = {}
        for error in data["errors"]:
            error_type = str(error["error"]).split(":")[0] if ":" in str(error["error"]) else "Unknown Error"
            if error_type in error_counts:
                error_counts[error_type] += 1
            else:
                error_counts[error_type] = 1
                
        error_df = pd.DataFrame({
            "Error Type": list(error_counts.keys()),
            "Count": list(error_counts.values()),
            "Percentage": [f"{(count/len(data['errors']))*100:.1f}%" for count in error_counts.values()]
        })
        st.dataframe(error_df)
    else:
        st.info("No errors recorded in the selected time period. Great job!")
        
    # Recent activity timeline
    st.subheader("Recent Activity")
    if data["timestamps"]:
        # Sort by timestamp
        timestamps = sorted(data["timestamps"], key=lambda x: x["timestamp"] if x["timestamp"] else datetime.now(), reverse=True)
        
        # Show last 10 activities
        recent = timestamps[:10]
        
        # Create a dataframe
        recent_df = pd.DataFrame({
            "Type": [item["type"] for item in recent],
            "Component": [item["component"] if item["component"] else "unknown" for item in recent],
            "Timestamp": [item["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if item["timestamp"] else "unknown" for item in recent]
        })
        
        st.dataframe(recent_df)
        
def _render_component_metrics(data: Dict[str, Any]):
    """Render component performance metrics."""
    st.header("Component Performance")
    
    if not data["components"]:
        st.info("No component data available")
        return
        
    # Display component usage breakdown
    st.subheader("Component Usage Distribution")
    
    fig, ax = plt.subplots()
    labels = list(data["components"].keys())
    values = list(data["components"].values())
    ax.bar(labels, values)
    ax.set_title('Component Usage')
    ax.set_xlabel('Component')
    ax.set_ylabel('Number of Runs')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig)
    
    # Calculate component success rates
    component_stats = {}
    
    for run_type, count in data["run_types"].items():
        # Extract component from run_type if possible, otherwise use "unknown"
        component = "unknown"
        for c in data["components"].keys():
            if c.lower() in run_type.lower():
                component = c
                break
                
        if component not in component_stats:
            component_stats[component] = {"total": 0, "success": 0, "errors": 0, "latency": []}
            
        component_stats[component]["total"] += count
    
    # Process latency by component
    for latency_item in data["latencies"]:
        component = latency_item.get("component", "unknown")
        if component not in component_stats:
            component_stats[component] = {"total": 0, "success": 0, "errors": 0, "latency": []}
            
        component_stats[component]["latency"].append(latency_item["latency"])
    
    # Process errors by component
    for error_item in data["errors"]:
        component = error_item.get("component", "unknown")
        if component not in component_stats:
            component_stats[component] = {"total": 0, "success": 0, "errors": 0, "latency": []}
            
        component_stats[component]["errors"] += 1
    
    # Create dataframe for component performance
    component_df_data = []
    
    for component, stats in component_stats.items():
        avg_latency = 0
        if stats["latency"]:
            avg_latency = sum(stats["latency"]) / len(stats["latency"])
            
        success_rate = 0
        if stats["total"] > 0:
            success_rate = ((stats["total"] - stats["errors"]) / stats["total"]) * 100
            
        component_df_data.append({
            "Component": component,
            "Total Runs": stats["total"],
            "Success Rate": f"{success_rate:.1f}%",
            "Avg Latency": f"{avg_latency:.2f}s",
            "Errors": stats["errors"]
        })
    
    component_df = pd.DataFrame(component_df_data)
    st.dataframe(component_df)
    
    # Component-specific insights
    st.subheader("Component Insights")
    
    # Allow selecting a component to analyze
    components = list(data["components"].keys())
    if components:
        selected_component = st.selectbox("Select a component to analyze", components)
        
        if selected_component:
            # Filter data for selected component
            component_latencies = [item for item in data["latencies"] if item.get("component") == selected_component]
            component_errors = [item for item in data["errors"] if item.get("component") == selected_component]
            
            # Display component metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Runs", data["components"].get(selected_component, 0))
            
            with col2:
                error_count = len(component_errors)
                total_runs = data["components"].get(selected_component, 0)
                success_rate = 0
                if total_runs > 0:
                    success_rate = ((total_runs - error_count) / total_runs) * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            with col3:
                avg_latency = 0
                if component_latencies:
                    latencies = [item["latency"] for item in component_latencies]
                    avg_latency = sum(latencies) / len(latencies)
                st.metric("Avg. Latency", f"{avg_latency:.2f}s")
            
            # Show recent errors for this component
            if component_errors:
                st.subheader(f"Recent errors for {selected_component}")
                error_df = pd.DataFrame({
                    "Error": [str(item["error"]) for item in component_errors[:5]],
                    "Timestamp": [item["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if item["timestamp"] else "unknown" for item in component_errors[:5]]
                })
                st.dataframe(error_df)
            else:
                st.success(f"No errors recorded for {selected_component} in the selected time period!")

def _render_latency_metrics(data: Dict[str, Any]):
    """Render latency analysis metrics."""
    st.header("Latency Analysis")
    
    if not data["latencies"]:
        st.info("No latency data available")
        return
    
    # Overall latency stats
    latencies = [item["latency"] for item in data["latencies"]]
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Latency", f"{avg_latency:.2f}s")
    with col2:
        st.metric("Maximum Latency", f"{max_latency:.2f}s")
    with col3:
        st.metric("Minimum Latency", f"{min_latency:.2f}s")
    
    # Latency distribution
    st.subheader("Latency Distribution")
    
    # Create histogram of latencies
    fig, ax = plt.subplots()
    ax.hist(latencies, bins=20)
    ax.set_title('Latency Distribution')
    ax.set_xlabel('Latency (s)')
    ax.set_ylabel('Number of Runs')
    st.pyplot(fig)
    
    # Latency by component
    st.subheader("Latency by Component")
    
    # Group latencies by component
    component_latencies = {}
    for item in data["latencies"]:
        component = item.get("component", "unknown")
        if component not in component_latencies:
            component_latencies[component] = []
        component_latencies[component].append(item["latency"])
    
    # Calculate average latency for each component
    component_avg_latencies = {}
    for component, latencies in component_latencies.items():
        component_avg_latencies[component] = sum(latencies) / len(latencies)
    
    # Create bar chart
    fig, ax = plt.subplots()
    components = list(component_avg_latencies.keys())
    averages = list(component_avg_latencies.values())
    ax.bar(components, averages)
    ax.set_title('Average Latency by Component')
    ax.set_xlabel('Component')
    ax.set_ylabel('Average Latency (s)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig)
    
    # Latency over time
    st.subheader("Latency Over Time")
    
    # Filter latencies with timestamps
    timed_latencies = [item for item in data["latencies"] if item["timestamp"]]
    
    if timed_latencies:
        # Sort by timestamp
        timed_latencies.sort(key=lambda x: x["timestamp"])
        
        # Create dataframe
        latency_df = pd.DataFrame({
            "Timestamp": [item["timestamp"] for item in timed_latencies],
            "Latency": [item["latency"] for item in timed_latencies],
            "Component": [item["component"] if item["component"] else "unknown" for item in timed_latencies]
        })
        
        # Create line chart
        fig, ax = plt.subplots()
        for component, group in latency_df.groupby("Component"):
            ax.plot(group["Timestamp"], group["Latency"], label=component)
        
        ax.set_title('Latency Over Time')
        ax.set_xlabel('Timestamp')
        ax.set_ylabel('Latency (s)')
        ax.legend()
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("No timestamp data available for latency trends")

def _render_prompt_metrics(data: Dict[str, Any], client: Client, project_name: str):
    """Render prompt analysis metrics."""
    st.header("Prompt Analysis")
    
    # Token usage stats
    if data["total_tokens"]:
        # Calculate token usage stats
        total_tokens = sum([item["tokens"] for item in data["total_tokens"]])
        prompt_tokens = sum([item["tokens"] for item in data["prompt_tokens"]]) if data["prompt_tokens"] else 0
        completion_tokens = sum([item["tokens"] for item in data["completion_tokens"]]) if data["completion_tokens"] else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tokens", f"{total_tokens:,}")
        with col2:
            st.metric("Prompt Tokens", f"{prompt_tokens:,}")
        with col3:
            st.metric("Completion Tokens", f"{completion_tokens:,}")
        
        # Total cost if available
        if data["costs"]:
            total_cost = sum([item["cost"] for item in data["costs"]])
            st.metric("Estimated Cost", f"${total_cost:.4f}")
    else:
        st.info("No token usage data available")
    
    # Prompt analysis tools
    st.subheader("Prompt Analysis Tools")
    
    # Fetch run details for a specific run
    run_id = st.text_input("Enter a run ID to analyze its prompts", "")
    
    if run_id:
        st.write("Fetching run details...")
        try:
            run = client.get_run(run_id)
            
            if run:
                st.success(f"Found run: {run.name}")
                
                # Display run metadata
                st.json({
                    "name": run.name,
                    "status": run.status if hasattr(run, "status") else "unknown",
                    "latency": run.latency if hasattr(run, "latency") else "unknown",
                    "start_time": str(run.start_time) if hasattr(run, "start_time") else "unknown",
                    "end_time": str(run.end_time) if hasattr(run, "end_time") else "unknown"
                })
                
                # Display prompts used
                st.subheader("Prompts Used")
                if hasattr(run, "inputs") and run.inputs:
                    for key, value in run.inputs.items():
                        st.write(f"**{key}:**")
                        st.code(value)
                else:
                    st.info("No prompt data available for this run")
                
                # Display completion
                st.subheader("Completion")
                if hasattr(run, "outputs") and run.outputs:
                    for key, value in run.outputs.items():
                        st.write(f"**{key}:**")
                        st.code(value)
                else:
                    st.info("No completion data available for this run")
                
                # Display token usage
                if hasattr(run, "usage") and run.usage:
                    st.subheader("Token Usage")
                    st.json({
                        "prompt_tokens": run.usage.prompt_tokens if hasattr(run.usage, "prompt_tokens") else "unknown",
                        "completion_tokens": run.usage.completion_tokens if hasattr(run.usage, "completion_tokens") else "unknown",
                        "total_tokens": run.usage.total_tokens if hasattr(run.usage, "total_tokens") else "unknown",
                        "cost": run.usage.cost if hasattr(run.usage, "cost") else "unknown"
                    })
            else:
                st.warning(f"No run found with ID: {run_id}")
        except Exception as e:
            st.error(f"Error fetching run: {str(e)}")
    
    # Prompt templates analysis
    st.subheader("Common Prompt Patterns")
    st.write("Analyze common patterns across your prompts to identify optimization opportunities.")
    
    # This would require more sophisticated analysis, placeholder for now
    st.info("Advanced prompt pattern analysis is under development. Check back soon for updates!")