import streamlit as st
import os
import logging
from dotenv import load_dotenv
from langsmith import Client

# Import our custom modules
from services.langsmith_config import setup_langsmith, track_prompt, get_project_metrics
from metrics.metrics_dashboard import render_metrics_dashboard

# Set up logging
logging.basicConfig(level=logging.INFO, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("langsmith_integration")

def initialize_langsmith():
    """
    Initialize LangSmith tracking in your application.
    This function should be called during app startup.
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Check for API key in environment
        langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
        
        if langsmith_api_key:
            logger.info("LangSmith API key found in environment")
            
            # Set in session state
            st.session_state.langsmith_api_key = langsmith_api_key
            st.session_state.langsmith_enabled = True
            
            # Set default project name
            project_name = os.getenv("LANGSMITH_PROJECT", "nav-assist")
            st.session_state.langsmith_project = project_name
            
            # Initialize LangSmith client
            client = setup_langsmith(langsmith_api_key)
            
            if client:
                logger.info(f"LangSmith initialized with project: {project_name}")
                
                # Store client in session state for reuse
                st.session_state.langsmith_client = client
                
                return True, "LangSmith successfully initialized"
            else:
                logger.warning("Failed to initialize LangSmith client")
                return False, "Failed to initialize LangSmith client"
        else:
            logger.info("No LangSmith API key found in environment")
            return False, "No LangSmith API key found"
    
    except Exception as e:
        logger.error(f"Error initializing LangSmith: {str(e)}")
        return False, f"Error: {str(e)}"

def track_sitemap_generation(url, max_depth, crawl_info, result):
    """
    Track sitemap generation metrics with LangSmith.
    Call this function after generating a sitemap.
    
    Args:
        url: Website URL
        max_depth: Maximum crawl depth
        crawl_info: Crawling configuration and stats
        result: Sitemap generation result
    """
    if not st.session_state.get('langsmith_enabled', False):
        return
    
    try:
        # Prepare inputs for tracking
        inputs = {
            "url": url,
            "max_depth": max_depth,
            "crawl_config": crawl_info
        }
        
        # Prepare a simplified version of the result for tracking
        result_summary = {
            "url": result.get("url", ""),
            "title": result.get("title", ""),
            "internal_link_count": result.get("internal_link_count", 0),
            "external_link_count": result.get("external_link_count", 0),
            "content_sections_count": len(result.get("content_sections", [])),
        }
        
        # Add metadata for filtering/analysis
        metadata = {
            "component": "sitemap_extractor",
            "domain": url.split("//")[-1].split("/")[0],
            "max_depth": max_depth,
            "execution_time": crawl_info.get("execution_time", 0)
        }
        
        # Track the run in LangSmith
        run_id = track_prompt(
            name="Website Sitemap Generation",
            prompts=inputs,
            completion=str(result_summary),
            metadata=metadata
        )
        
        logger.info(f"Sitemap generation tracked in LangSmith with run ID: {run_id}")
        return run_id
    
    except Exception as e:
        logger.error(f"Error tracking sitemap generation: {str(e)}")
        return None

def track_agent_task(task, system_prompt, base_url, result, execution_time=None):
    """
    Track agent task metrics with LangSmith.
    Call this function after executing an agent task.
    
    Args:
        task: Agent task description
        system_prompt: System prompt used
        base_url: Base URL for the task
        result: Task execution result
        execution_time: Time taken to execute the task (optional)
    """
    if not st.session_state.get('langsmith_enabled', False):
        return
    
    try:
        # Prepare inputs for tracking
        inputs = {
            "task": task,
            "system_prompt": system_prompt,
            "base_url": base_url
        }
        
        # Check if we need to truncate result for tracking
        tracked_result = result
        if len(str(tracked_result)) > 8000:  # Avoid very large payloads
            tracked_result = str(tracked_result)[:4000] + "... [truncated] ..." + str(tracked_result)[-4000:]
        
        # Add metadata for filtering/analysis
        metadata = {
            "component": "browser_agent",
            "domain": base_url.split("//")[-1].split("/")[0] if base_url else None,
            "result_length": len(str(result)),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o")
        }
        
        # Add execution time if available
        if execution_time:
            metadata['execution_time'] = execution_time
        
        # Track the run in LangSmith
        run_id = track_prompt(
            name="Browser Agent Task",
            prompts=inputs,
            completion=str(tracked_result),
            metadata=metadata
        )
        
        logger.info(f"Agent task tracked in LangSmith with run ID: {run_id}")
        return run_id
    
    except Exception as e:
        logger.error(f"Error tracking agent task: {str(e)}")
        return None

def track_query_mapping(user_query, navigation_data, mapped_pages, execution_time=None):
    """
    Track query mapping metrics with LangSmith.
    Call this function after mapping a user query to website sections.
    
    Args:
        user_query: User's query text
        navigation_data: Website navigation structure
        mapped_pages: Resulting mapped pages
        execution_time: Time taken to execute the mapping (optional)
    """
    if not st.session_state.get('langsmith_enabled', False):
        return
    
    try:
        # Prepare inputs for tracking
        inputs = {
            "user_query": user_query,
            "website_structure": navigation_data
        }
        
        # Prepare tracking output
        output = {
            "relevant_pages": mapped_pages,
            "total_matches": len(mapped_pages),
            "top_score": mapped_pages[0]['score'] if mapped_pages else 0
        }
        
        # Add metadata for filtering/analysis
        metadata = {
            "component": "query_mapping",
            "query_length": len(user_query),
            "nav_items_count": len(navigation_data) if navigation_data else 0,
            "model": "gpt-3.5-turbo"
        }
        
        # Add execution time if available
        if execution_time:
            metadata['execution_time'] = execution_time
        
        # Track the run in LangSmith
        run_id = track_prompt(
            name="Query Mapping Analysis",
            prompts=inputs,
            completion=str(output),
            metadata=metadata
        )
        
        logger.info(f"Query mapping tracked in LangSmith with run ID: {run_id}")
        return run_id
    
    except Exception as e:
        logger.error(f"Error tracking query mapping: {str(e)}")
        return None

def display_metrics_dashboard():
    """
    Display the LangSmith metrics dashboard.
    Call this function to render the metrics UI.
    """
    if not st.session_state.get('langsmith_enabled', False):
        st.warning("LangSmith metrics tracking is not enabled. Please enable it in the Settings tab.")
        
        # Add a button to enable LangSmith
        if st.button("Enable LangSmith Tracking"):
            st.session_state.sidebar_active_tab = "Settings"
            st.rerun()
        
        return
    
    # Render the metrics dashboard
    render_metrics_dashboard()

def main():
    """Example usage of LangSmith integration."""
    st.title("LangSmith Integration Demo")
    
    # Initialize LangSmith
    if 'langsmith_enabled' not in st.session_state:
        success, message = initialize_langsmith()
        
        if success:
            st.success(message)
        else:
            st.warning(message)
            
            # Provide a form to enter API key manually
            with st.form("langsmith_key_form"):
                langsmith_key = st.text_input("Enter LangSmith API Key", type="password")
                project_name = st.text_input("Project Name", value="nav-assist")
                submit_langsmith = st.form_submit_button("Enable LangSmith")
                
                if submit_langsmith and langsmith_key:
                    st.session_state.langsmith_api_key = langsmith_key
                    st.session_state.langsmith_enabled = True
                    st.session_state.langsmith_project = project_name
                    
                    # Set environment variables
                    os.environ["LANGSMITH_API_KEY"] = langsmith_key
                    os.environ["LANGSMITH_PROJECT"] = project_name
                    
                    st.success("LangSmith tracking enabled!")
                    st.rerun()
    
    # Demo tracking of a sitemap generation
    st.header("Demo: Track Sitemap Generation")
    if st.button("Track Sample Sitemap Generation"):
        with st.spinner("Tracking sample sitemap generation..."):
            # Simulate a sitemap generation
            url = "https://example.com"
            max_depth = 3
            crawl_info = {"execution_time": 2.5, "pages_crawled": 10}
            result = {
                "url": url,
                "title": "Example Website",
                "internal_link_count": 25,
                "external_link_count": 8,
                "content_sections": [{"heading": "Section 1"}, {"heading": "Section 2"}]
            }
            
            run_id = track_sitemap_generation(url, max_depth, crawl_info, result)
            
            if run_id:
                st.success(f"Sitemap generation tracked with run ID: {run_id}")
            else:
                st.error("Failed to track sitemap generation")
    
    # Demo tracking of an agent task
    st.header("Demo: Track Agent Task")
    if st.button("Track Sample Agent Task"):
        with st.spinner("Tracking sample agent task..."):
            # Simulate an agent task
            task = "Find pricing information on the website"
            system_prompt = "You are a website navigator. Find pricing information."
            base_url = "https://example.com"
            result = "Found pricing on the Pricing page: Basic plan $10/month, Pro plan $25/month"
            execution_time = 3.2
            
            run_id = track_agent_task(task, system_prompt, base_url, result, execution_time)
            
            if run_id:
                st.success(f"Agent task tracked with run ID: {run_id}")
            else:
                st.error("Failed to track agent task")
    
    # Demo tracking of query mapping
    st.header("Demo: Track Query Mapping")
    if st.button("Track Sample Query Mapping"):
        with st.spinner("Tracking sample query mapping..."):
            # Simulate query mapping
            user_query = "Where can I find pricing information?"
            navigation_data = [
                {"text": "Home", "url": "/"},
                {"text": "Products", "url": "/products"},
                {"text": "Pricing", "url": "/pricing"},
                {"text": "Contact", "url": "/contact"}
            ]
            mapped_pages = [
                {"title": "Pricing", "url": "/pricing", "score": 9.5, "matched_topics": ["pricing", "information"]},
                {"title": "Products", "url": "/products", "score": 4.2, "matched_topics": ["information"]}
            ]
            execution_time = 0.8
            
            run_id = track_query_mapping(user_query, navigation_data, mapped_pages, execution_time)
            
            if run_id:
                st.success(f"Query mapping tracked with run ID: {run_id}")
            else:
                st.error("Failed to track query mapping")
    
    # Display metrics dashboard
    st.header("Metrics Dashboard")
    if st.button("Show Metrics Dashboard"):
        display_metrics_dashboard()

if __name__ == "__main__":
    main()