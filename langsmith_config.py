import os
import logging
from typing import Optional, Dict, Any, List
from langsmith import Client
import streamlit as st
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger("langsmith_config")

def setup_langsmith(api_key: Optional[str] = None) -> Optional[Client]:
    """
    Initialize LangSmith client with error handling.
    
    Args:
        api_key: LangSmith API key (optional, can use env var)
        
    Returns:
        LangSmith client or None if setup fails
    """
    try:
        # Check for API key in order: provided key, session state, environment variable
        langsmith_api_key = api_key or st.session_state.get('langsmith_api_key') or os.getenv("LANGSMITH_API_KEY")
        
        if not langsmith_api_key:
            logger.warning("No LangSmith API key found. Metrics tracking disabled.")
            return None
        
        # Set environment variables for LangSmith
        os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
        
        # Set project name if not already set
        if "LANGSMITH_PROJECT" not in os.environ:
            os.environ["LANGSMITH_PROJECT"] = "nav-assist"
        
        # Initialize client
        client = Client(api_key=langsmith_api_key)
        logger.info(f"LangSmith initialized with project: {os.getenv('LANGSMITH_PROJECT')}")
        
        return client
    
    except Exception as e:
        logger.error(f"Error initializing LangSmith: {str(e)}")
        return None

def track_prompt(
    name: str, 
    prompts: Dict[str, Any], 
    completion: str, 
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Track a prompt and its completion in LangSmith.
    
    Args:
        name: Name of the run
        prompts: Dictionary of prompt inputs
        completion: Model completion
        metadata: Additional metadata
        
    Returns:
        Run ID if successful, empty string otherwise
    """
    try:
        # Get LangSmith client
        client = setup_langsmith()
        if not client:
            return ""
        
        # Create run
        run_id = client.create_run(
            name=name,
            inputs=prompts,
            outputs={"completion": completion},
            metadata=metadata or {},
            runtime=os.getenv("LANGSMITH_PROJECT", "nav-assist")
        )
        
        logger.info(f"LangSmith run created: {run_id}")
        return run_id
    
    except Exception as e:
        logger.error(f"Error tracking prompt: {str(e)}")
        return ""

def get_project_metrics(project_name: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
    """
    Get enhanced metrics for a LangSmith project.
    
    Args:
        project_name: Name of project (default: from env var)
        days: Number of days to look back for metrics
        
    Returns:
        Dictionary of metrics
    """
    try:
        # Get LangSmith client
        client = setup_langsmith()
        if not client:
            return {"error": "LangSmith client not initialized"}
        
        # Use provided project name or default
        project = project_name or os.getenv("LANGSMITH_PROJECT", "nav-assist")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get runs for project with date filter
        runs = client.list_runs(
            project_name=project, 
            start_time=start_date,
            end_time=end_date,
            limit=200
        )
        
        # Convert to list if it's an iterator
        runs_list = list(runs)
        
        # Aggregate metrics
        metrics = {
            "total_runs": 0,
            "avg_latency": 0,
            "success_rate": 0,
            "run_types": {},
            "component_stats": {},
            "websites_analyzed": set(),
            "queries_by_type": {},
            "most_recent_runs": [],
            "daily_stats": {},
            "error_types": {}
        }
        
        # Process runs
        total_latency = 0
        successes = 0
        
        for run in runs_list:
            metrics["total_runs"] += 1
            
            # Collect timestamps for daily stats
            run_date = None
            if hasattr(run, "start_time") and run.start_time:
                run_date = run.start_time.strftime('%Y-%m-%d')
                if run_date not in metrics["daily_stats"]:
                    metrics["daily_stats"][run_date] = {"count": 0, "success": 0}
                metrics["daily_stats"][run_date]["count"] += 1
            
            # Latency calculation
            if hasattr(run, "latency") and run.latency:
                total_latency += run.latency
            
            # Success tracking
            is_success = False
            if hasattr(run, "status") and run.status == "SUCCESS":
                successes += 1
                is_success = True
                if run_date:
                    metrics["daily_stats"][run_date]["success"] += 1
            
            # Run type counting
            run_type = run.name if hasattr(run, "name") else "unknown"
            if run_type in metrics["run_types"]:
                metrics["run_types"][run_type] += 1
            else:
                metrics["run_types"][run_type] = 1
                
            # Track component statistics
            component = "unknown"
            if hasattr(run, "metadata") and run.metadata and "component" in run.metadata:
                component = run.metadata["component"]
                
                # Initialize component stats if needed
                if component not in metrics["component_stats"]:
                    metrics["component_stats"][component] = {
                        "count": 0,
                        "success": 0,
                        "avg_latency": 0,
                        "total_latency": 0
                    }
                
                # Update component metrics
                metrics["component_stats"][component]["count"] += 1
                if is_success:
                    metrics["component_stats"][component]["success"] += 1
                if hasattr(run, "latency") and run.latency:
                    metrics["component_stats"][component]["total_latency"] += run.latency
            
            # Collect website domains analyzed
            if hasattr(run, "metadata") and run.metadata and "domain" in run.metadata:
                domain = run.metadata["domain"]
                if domain:
                    metrics["websites_analyzed"].add(domain)
            
            # Track query types (for Browser Agent Task)
            if run_type == "Browser Agent Task":
                task_type = "other"
                task = ""
                
                # Try to extract task from inputs
                if hasattr(run, "inputs") and "task" in run.inputs:
                    task = run.inputs["task"]
                    # Categorize task by keywords
                    if any(keyword in task.lower() for keyword in ["find", "search", "look for", "where"]):
                        task_type = "information_finding"
                    elif any(keyword in task.lower() for keyword in ["what is", "describe", "explain", "tell me about"]):
                        task_type = "explanation"
                    elif any(keyword in task.lower() for keyword in ["how to", "steps", "procedure", "process"]):
                        task_type = "how_to"
                    elif any(keyword in task.lower() for keyword in ["contact", "email", "phone", "reach"]):
                        task_type = "contact_info"
                    elif any(keyword in task.lower() for keyword in ["price", "cost", "subscription", "plan"]):
                        task_type = "pricing"
                
                # Update query type stats
                if task_type in metrics["queries_by_type"]:
                    metrics["queries_by_type"][task_type] += 1
                else:
                    metrics["queries_by_type"][task_type] = 1
            
            # Add to most recent runs (keep only the 5 most recent)
            if hasattr(run, "start_time") and hasattr(run, "outputs"):
                # Get a preview of the output
                output_preview = ""
                if "completion" in run.outputs:
                    output_text = run.outputs["completion"]
                    if isinstance(output_text, str):
                        output_preview = output_text[:100] + "..." if len(output_text) > 100 else output_text
                
                # Add to recent runs
                recent_run = {
                    "run_id": run.id,
                    "type": run_type,
                    "component": component,
                    "timestamp": run.start_time,
                    "output_preview": output_preview,
                    "success": is_success
                }
                
                # Add to most recent runs list and sort by timestamp
                metrics["most_recent_runs"].append(recent_run)
                metrics["most_recent_runs"] = sorted(
                    metrics["most_recent_runs"], 
                    key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min, 
                    reverse=True
                )[:5]
            
            # Error tracking
            if hasattr(run, "error") and run.error:
                error_type = type(run.error).__name__
                if error_type in metrics["error_types"]:
                    metrics["error_types"][error_type] += 1
                else:
                    metrics["error_types"][error_type] = 1
        
        # Calculate averages
        if metrics["total_runs"] > 0:
            metrics["avg_latency"] = total_latency / metrics["total_runs"]
            metrics["success_rate"] = (successes / metrics["total_runs"]) * 100
        
        # Calculate component averages
        for component, stats in metrics["component_stats"].items():
            if stats["count"] > 0:
                stats["avg_latency"] = stats["total_latency"] / stats["count"]
                stats["success_rate"] = (stats["success"] / stats["count"]) * 100
        
        # Convert websites_analyzed to list for JSON serialization
        metrics["websites_analyzed"] = list(metrics["websites_analyzed"])
        
        # Convert daily_stats to a format suitable for graphing
        metrics["daily_usage"] = [
            {"date": date, "runs": stats["count"], "success": stats["success"]}
            for date, stats in metrics["daily_stats"].items()
        ]
        metrics["daily_usage"].sort(key=lambda x: x["date"])
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error getting project metrics: {str(e)}")
        return {"error": str(e)}