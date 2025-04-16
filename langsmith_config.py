import os
import logging
from typing import Optional, Dict, Any
from langsmith import Client
import streamlit as st

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

def get_project_metrics(project_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get metrics for a LangSmith project.
    
    Args:
        project_name: Name of project (default: from env var)
        
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
        
        # Get runs for project
        runs = client.list_runs(project_name=project, limit=100)
        
        # Aggregate metrics
        metrics = {
            "total_runs": 0,
            "avg_latency": 0,
            "success_rate": 0,
            "run_types": {},
            "error_types": {}
        }
        
        # Process runs
        total_latency = 0
        successes = 0
        
        for run in runs:
            metrics["total_runs"] += 1
            
            # Latency calculation
            if hasattr(run, "latency") and run.latency:
                total_latency += run.latency
            
            # Success tracking
            if hasattr(run, "status") and run.status == "SUCCESS":
                successes += 1
            
            # Run type counting
            run_type = run.name if hasattr(run, "name") else "unknown"
            if run_type in metrics["run_types"]:
                metrics["run_types"][run_type] += 1
            else:
                metrics["run_types"][run_type] = 1
            
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
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error getting project metrics: {str(e)}")
        return {"error": str(e)}