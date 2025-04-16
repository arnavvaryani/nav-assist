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

def run_agent_task(task: str, api_key: Optional[str] = None, headless: bool = True, 
                  browser_width: int = 1280, browser_height: int = 800) -> str:
    """
    Runs the web agent with the provided task.
    
    Args:
        task: The task for the agent to perform
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
        
        # Run the task using async function
        result = asyncio.run(_run_agent_async(context, task, llm))
        
        logger.info(f"Agent task completed successfully: {task[:50]}...")
        return result
        
    except Exception as e:
        error_msg = f"Error running agent task: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise Exception(error_msg)

async def _run_agent_async(context, task, llm):
    """Run the agent asynchronously."""
    try:
        # Initialize the agent
        agent = Agent(
            browser_context=context,
            task=task,
            llm=llm,
        )
        
        # Run the agent
        result = await agent.run()
        
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
    """Format the agent result for better readability.
    
    This function can be expanded to parse and format the results
    in a more structured way depending on the task type.
    """
    # For now, just return the result directly
    # This can be expanded to provide better formatting later
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