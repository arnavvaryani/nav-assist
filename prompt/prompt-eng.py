import streamlit as st
import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize conversation state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# All control widgets are placed in the sidebar
with st.sidebar:
    st.header("Automation Controls")
    gemini_api_key = st.text_input("Enter Google Gemini API key", type="password")
    st.markdown("Your Gemini API key is required for calling Gemini API with web search.")
    user_prompt = st.text_area(
        "Enter your prompt to automate website search using Selenium:",
        help="Example: 'Find the admissions requirements on https://www.northeastern.edu/'"
    )
    search_website = st.text_input(
        "Enter the website where you want to search content:",
        help="Example: 'northeastern.edu' (Do not include https://)"
    )
    search_query = st.text_input(
        "Enter your search query for the specified website:",
        help="Example: 'University Leadership team' (Gemini will search only on the specified website)"
    )
    generate_code = st.button("Generate Selenium Code")
    execute_code = st.button("Execute Generated Code")
    get_search_results = st.button("Get AI Website Search Results")

# Main area displays a ChatGPT‑clone style conversation UI
st.title("ChatGPT Clone - Automation Assistant")

# Initialize Gemini API if API key is provided
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

def clean_code_fences(code_str: str) -> str:
    """
    Remove leading or trailing triple-backtick fences (e.g. ```python ... ```).
    """
    code_str = code_str.strip()
    if code_str.startswith("```python"):
        code_str = code_str[len("```python"):].strip()
    elif code_str.startswith("```"):
        code_str = code_str[len("```"):].strip()
    if code_str.endswith("```"):
        code_str = code_str[: -len("```")].strip()
    return code_str

def get_ai_website_search_results(website, query):
    """
    Uses Gemini AI to search for content only within the specified website.
    Extracts relevant pages and summaries.
    """
    try:
        if not website or not query:
            return "Please enter both a website and a search query."
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        Search for information on the website '{website}' about: '{query}'.
        Extract the most relevant information from the available webpages.
        Identify the URLs within '{website}' where this information can be found.
        Provide:
        1. A summarized answer based only on content from '{website}'.
        2. A list of URLs within '{website}' that contain relevant details.
        
        IMPORTANT: Include a very detailed chain-of-thought explaining your reasoning and a section of self-criticism discussing potential pitfalls or improvements.
        Format these as a comment block at the end of your output.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error fetching AI search results: {e}"

def generate_selenium_code(user_prompt, search_website):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Attempt to manually extract a snippet of the page source
        page_source_snippet = ""
        if search_website.strip():
            # Prepend scheme if missing
            if not search_website.lower().startswith("http"):
                url = "https://" + search_website.strip()
            else:
                url = search_website.strip()
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    full_source = response.text
                    # Limit to first 1000 characters for prompt brevity
                    snippet = full_source[:1000]
                    page_source_snippet = f"Page Source Snippet:\n{snippet}\n"
                else:
                    page_source_snippet = f"Error retrieving page source: HTTP {response.status_code}"
            except Exception as e:
                page_source_snippet = f"Error retrieving page source: {e}"
        
        website_instruction = ""
        if search_website.strip():
            website_instruction = f"Target website: '{search_website.strip()}'."
        
        prompt = f"""
        You are an expert in web automation. Your task is to generate an efficient **Python Selenium script** that finds the requested information on the website specified.
        
        {website_instruction}
        
        {page_source_snippet}
        
        **Instructions:**
        1. **Use Google Search** to find the best way to navigate the website.
        2. **Check if sitemap.xml exists** on the website. If it does, extract important URLs.
        3. **Extract and analyze the page source** after loading the website to identify key navigational elements (such as menus, headers, or footers).
        4. **Determine the optimal navigation strategy** based on the extracted page source and available navigation elements.
        5. **Generate an optimized Selenium script** that:
            - Assumes WebDriver is already installed and set up in the environment.
            - Opens the website using Chrome WebDriver.
            - Extracts the page source (e.g., using `driver.page_source`) and uses it to inform navigation.
            - Searches dynamically for the requested information.
            - Uses the best approach (site search, menus, or direct links).
            - Clicks the most relevant result and navigates to the appropriate page.
            - Waits for elements to load properly.
            - Prints the final page title to confirm success.
            - Handles errors and ensures the browser closes correctly.
        
        **User's Request:**  
        '{user_prompt}'
        
        IMPORTANT: At the end of your generated code, include a very detailed chain-of-thought describing your reasoning process and add a section with self-criticism highlighting any potential shortcomings or improvements.
        Make sure these are included as comments within the code.
        
        Only return **executable Python code** with the additional comment block for chain-of-thought and self-criticism.
        """
        response = model.generate_content(prompt)
        generated_code = clean_code_fences(response.text)
        return generated_code
    except Exception as e:
        return f"Error generating Selenium code: {e}"

# Process sidebar button actions and update conversation history
if generate_code:
    if not gemini_api_key:
        st.session_state.messages.append({"role": "assistant", "content": "Please enter your Gemini API key."})
    elif not user_prompt.strip():
        st.session_state.messages.append({"role": "assistant", "content": "Please enter a valid prompt."})
    else:
        code = generate_selenium_code(user_prompt, search_website)
        st.session_state.generated_code = code
        st.session_state.messages.append({"role": "user", "content": f"Generate Selenium Code for:\n\n{user_prompt}"})
        st.session_state.messages.append({"role": "assistant", "content": f"Generated Selenium Code:\n```\n{code}\n```"})

if execute_code:
    if "generated_code" not in st.session_state:
        st.session_state.messages.append({"role": "assistant", "content": "No Selenium code generated yet."})
    else:
        try:
            local_namespace = {}
            exec(st.session_state.generated_code, local_namespace)
            st.session_state.messages.append({"role": "assistant", "content": "Selenium code executed successfully. Check the console for output."})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error executing Selenium code: {e}"})

if get_search_results:
    if not gemini_api_key:
        st.session_state.messages.append({"role": "assistant", "content": "Please enter your Gemini API key."})
    elif not search_website.strip() or not search_query.strip():
        st.session_state.messages.append({"role": "assistant", "content": "Please enter both a website and a search query."})
    else:
        results = get_ai_website_search_results(search_website, search_query)
        st.session_state.messages.append({"role": "user", "content": f"Search Website: {search_website} with query: {search_query}"})
        st.session_state.messages.append({"role": "assistant", "content": f"AI-Powered Search Results:\n\n{results}"})

# Add a chat input section in the main area
user_chat = st.chat_input("Say something")
if user_chat:
    st.session_state.messages.append({"role": "user", "content": user_chat})
    # For demo purposes, the assistant echoes the user input.
    st.session_state.messages.append({"role": "assistant", "content": f"You said: {user_chat}"})

# Display conversation messages using Streamlit's chat message UI
for message in st.session_state.messages:
    if message["role"] == "user":
        st.chat_message("user", avatar="🧑").markdown(message["content"])
    else:
        st.chat_message("assistant", avatar="🤖").markdown(message["content"])