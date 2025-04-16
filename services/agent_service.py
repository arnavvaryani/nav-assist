import asyncio
import traceback
import logging
import os
from typing import Dict, Any, Optional, List

from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser
from browser_use.browser.context import BrowserContextConfig, BrowserContext

# Set up logging
logger = logging.getLogger("agent_service")

def run_agent_task(
    task: str, 
    system_prompt: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None, 
    headless: bool = True, 
    browser_width: int = 1280, 
    browser_height: int = 800
) -> str:
    """
    Runs the web agent with the provided task.
    
    Args:
        task: The task for the agent to perform
        system_prompt: Optional system prompt with website knowledge
        base_url: Base URL to start navigation from
        api_key: OpenAI API key (uses env var if not provided)
        headless: Whether to run browser in headless mode
        browser_width: Browser window width
        browser_height: Browser window height
        
    Returns:
        The agent's result as a string
    """
    logger.info(f"Starting agent task: {task[:50]}...")
    
    try:
        # Use provided API key or get from environment
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # Create browser configuration
        browser_config = BrowserConfig(
            headless=headless, 
            disable_security=True
        )
        
        # Create browser context configuration
        context_config = BrowserContextConfig(
            wait_for_network_idle_page_load_time=3.0,
            browser_window_size={'width': browser_width, 'height': browser_height},
            locale='en-US',
            highlight_elements=True,
            viewport_expansion=500,
        )
        
        logger.info("Initializing browser...")
        
        # Initialize browser and context
        browser = Browser(config=browser_config)
        context = BrowserContext(browser=browser, config=context_config)
        
        # Initialize the language model
        logger.info("Initializing language model...")
        llm = ChatOpenAI(model="gpt-4o")
        
        logger.info("Running agent task...")
        
        # Prepare the complete task with context
        complete_task = task
        
        # Add base URL if provided
        if base_url:
            complete_task = f"Start by navigating to {base_url} and then {task}"
        
        # Run the task using async function
        result = asyncio.run(_run_agent_async(context, complete_task, llm, system_prompt))
        
        logger.info(f"Agent task completed successfully: {task[:50]}...")
        return result
        
    except Exception as e:
        error_msg = f"Error running agent task: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

async def _run_agent_async(context, task, llm, system_prompt=None):
    """
    Run the agent asynchronously.
    
    Args:
        context: Browser context
        task: User task
        llm: Language model
        system_prompt: Optional system prompt
    """
    try:
        # Initialize the agent with optional system prompt
        agent_kwargs = {
            "browser_context": context,
            "task": task,
            "llm": llm,
        }
        
        # Add system prompt if provided
        if system_prompt:
            agent_kwargs["system_prompt"] = system_prompt
            logger.info("Using custom system prompt with site structure information")
        
        # Initialize the agent
        agent = Agent(**agent_kwargs)
        
        # Run the agent
        agent_history = await agent.run()
        
        # Convert the agent history to a string representation
        # The agent might return AgentHistoryList object instead of a string
        if hasattr(agent_history, 'to_string'):
            # Use the to_string method if available
            result = agent_history.to_string()
        elif hasattr(agent_history, '__str__'):
            # Fall back to the string representation
            result = str(agent_history)
        else:
            # Handle unexpected return type
            result = f"Completed task: {task}\n\nAgent returned results in an unsupported format."
        
        # If result is a byte string, decode it
        if isinstance(result, bytes):
            result = result.decode('utf-8', errors='ignore')
            
        # Format the result for better readability
        formatted_result = _format_agent_result(result, task)
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"Error in async agent execution: {str(e)}")
        logger.error(traceback.format_exc())
        raise e

def _format_agent_result(result: str, task: str) -> str:
    """
    Format the agent result for better readability.
    
    Args:
        result: Raw agent result
        task: User task
        
    Returns:
        Formatted result string
    """
    try:
        # If the result is extremely long, we might want to summarize it
        if len(result) > 10000:
            # Extract key sections or truncate intelligently
            formatted_result = result[:10000] + "\n\n[... Additional content truncated ...]"
        else:
            formatted_result = result
            
        # Add a header to the result
        header = f"# Results for: {task}\n\n"
        
        # If the result doesn't already have structured sections, add them
        if "## Summary" not in formatted_result:
            # Add some basic structure
            formatted_result = header + formatted_result
        else:
            formatted_result = header + formatted_result
            
        return formatted_result
    
    except Exception as e:
        logger.error(f"Error formatting agent result: {str(e)}")
        # Return original result if formatting fails
        return result

def get_agent_status():
    """Get information about agent capabilities and status."""
    try:
        # Check if browser-use is available
        try:
            import browser_use
            browser_use_available = True
        except ImportError:
            browser_use_available = False
        
        # Check if OpenAI API key is set
        api_key_set = "OPENAI_API_KEY" in os.environ or os.getenv("OPENAI_API_KEY") is not None
        
        # Check Chrome/ChromeDriver availability
        try:
            # Try to create a browser instance to check availability
            browser_config = BrowserConfig(headless=True)
            browser = Browser(config=browser_config)
            browser_available = True
            # Close the browser after checking
            browser.teardown()
        except Exception:
            browser_available = False
        
        return {
            "browser_use_available": browser_use_available,
            "api_key_set": api_key_set,
            "browser_available": browser_available,
            "agent_ready": browser_use_available and api_key_set and browser_available
        }
    except Exception as e:
        logger.error(f"Error checking agent status: {str(e)}")
        return {
            "browser_use_available": False,
            "api_key_set": False,
            "browser_available": False,
            "agent_ready": False,
            "error": str(e)
        }