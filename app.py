import asyncio
import nest_asyncio
nest_asyncio.apply()

from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser
from browser_use.browser.context import BrowserContextConfig, BrowserContext
from dotenv import load_dotenv
import os


# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Configure browser
browser_config = BrowserConfig(headless=False, disable_security=True)
context_config = BrowserContextConfig(
    wait_for_network_idle_page_load_time=3.0,
    browser_window_size={'width': 1280, 'height': 1100},
    locale='en-US',
    highlight_elements=True,
    viewport_expansion=500,
)

browser = Browser(config=browser_config)
context = BrowserContext(browser=browser, config=context_config)
llm = ChatOpenAI(model="gpt-4o")

# Main runner using asyncio (wrapped properly)
def run_agent(task_override=None):
    final_task = task_override if task_override else "Find the cheapest nonstop flight from Dubai to COK (Cochin) in economy class for tomorrow for one passenger."

    async def agent_runner():
        print("[DEBUG] Running agent with task:", final_task)
        agent = Agent(
            browser_context=context,
            task=final_task,
            llm=llm,
        )
        print("[DEBUG] Agent initialized. Running task...")
        result = await agent.run()
        print("[DEBUG] Agent finished. Result:", result.encode('utf-8', errors='ignore').decode('utf-8'))
        return result

    return asyncio.run(agent_runner())
