import streamlit as st
import asyncio
import nest_asyncio
nest_asyncio.apply()

from dotenv import load_dotenv
import os

# Load environment variables from .env file if available
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Import the required libraries for the agent
from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser
from browser_use.browser.context import BrowserContextConfig, BrowserContext

# Configure the browser for agent usage
browser_config = BrowserConfig(headless=False, disable_security=True)
context_config = BrowserContextConfig(
    wait_for_network_idle_page_load_time=3.0,
    browser_window_size={'width': 1280, 'height': 1100},
    locale='en-US',
    highlight_elements=True,
    viewport_expansion=500,
)

# Create browser and context instances
browser = Browser(config=browser_config)
context = BrowserContext(browser=browser, config=context_config)

# Initialize the language model (ensure you have access to GPT-4o or adjust the model name accordingly)
llm = ChatOpenAI(model="gpt-4o")

def run_agent(task_override=None):
    """
    Runs the web agent with the provided task.
    
    If no task is provided, a default task is used.
    The function executes the agent asynchronously and returns the final result.
    """
    # Use the provided task or fall back to a default task prompt
    final_task = task_override if task_override else (
        "Find the cheapest nonstop flight from Dubai to COK (Cochin) in economy class for tomorrow for one passenger."
    )
    
    async def agent_runner():
        st.write("[DEBUG] Running agent with task: " + final_task)
        agent = Agent(
            browser_context=context,
            task=final_task,
            llm=llm,
        )
        st.write("[DEBUG] Agent initialized. Running task...")
        result = await agent.run()
        # If result is a byte string, decode it into a normal string
        if isinstance(result, bytes):
            result = result.decode('utf-8', errors='ignore')
        st.write("[DEBUG] Agent finished.")
        return result

    return asyncio.run(agent_runner())

# --- Streamlit UI ---
st.set_page_config(page_title="LangChain Web Agent", layout="centered")
st.title("🧠 Web Automation Agent")
st.markdown("Type what you want your agent to find or do on the web!")

# Example prompts to help guide the user
examples = [
    "Find the best deals on iPhones in India",
    "List all video game releases in April 2025",
    "What are the top 5 headlines in tech today?",
    "Compare prices for noise-cancelling headphones",
    "Find cheap hotels in Tokyo for next weekend"
]

# Text area for the user to input their task prompt
task_input = st.text_area("📝 Enter your task prompt:", value=examples[0], height=100)

# When the user clicks the "Run Agent" button, run the agent
if st.button("🚀 Run Agent"):
    with st.spinner("Agent is navigating the web..."):
        try:
            # Run the agent with the provided task
            result = run_agent(task_input)
            st.success("✅ Task Completed")
            st.write("### 🔍 Result")
            st.code(result, language="text")
        except Exception as e:
            st.error("💥 Agent crashed")
            st.code(str(e))
