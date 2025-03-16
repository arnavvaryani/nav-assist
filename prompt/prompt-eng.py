import streamlit as st
import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import traceback
import concurrent.futures

# Load environment variables
load_dotenv()

# Initialize conversation state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []
if "website_structure" not in st.session_state:
    st.session_state.website_structure = None

# All control widgets are placed in the sidebar
with st.sidebar:
    st.header("Automation Controls")
    gemini_api_key = st.text_input("Enter Google Gemini API key", type="password")
    st.markdown("Your Gemini API key is required for calling Gemini API.")
    
    st.subheader("Website Navigation")
    search_website = st.text_input(
        "Enter website to analyze:",
        help="Example: 'northeastern.edu' (Do not include https://)"
    )
    analyze_site_button = st.button("Analyze Website Structure")
    
    st.subheader("Information Search")
    search_query = st.text_input(
        "What information are you looking for?",
        help="Example: 'Research programs' or 'Admissions requirements'"
    )
    get_navigation_path = st.button("Find Navigation Path")
    
    st.subheader("Automation")
    user_prompt = st.text_area(
        "Enter prompt for Selenium automation:",
        help="Example: 'Find the admissions requirements on northeastern.edu'"
    )
    generate_code = st.button("Generate Selenium Code")
    execute_code = st.button("Execute Generated Code")

# Main area displays conversation UI
st.title("Website Navigation Assistant")

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

def is_navigation_element(element, class_name=None):
    """Check if an element is likely a navigation element based on its attributes and content."""
    if not element:
        return False
        
    # Check tag name
    if element.name in ['nav', 'menu', 'ul', 'ol']:
        return True
        
    # Check class and id attributes
    if class_name and any(nav_term in class_name.lower() for nav_term in ['nav', 'menu', 'topbar', 'header', 'main-menu']):
        return True
        
    # Check id attribute
    element_id = element.get('id', '').lower()
    if any(nav_term in element_id for nav_term in ['nav', 'menu', 'topbar', 'header']):
        return True
        
    # Check if element contains multiple links in a list-like structure
    links = element.find_all('a', recursive=False)
    if len(links) >= 3:
        return True
        
    return False

def extract_navigation_links(element):
    """Extract navigation links from an element."""
    links = []
    if not element:
        return links
        
    # Extract direct links
    for link in element.find_all('a'):
        if link.text.strip():
            href = link.get('href', '')
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                links.append({
                    "text": link.text.strip(),
                    "url": href
                })
                
    return links

def analyze_website_structure(url):
    """Extract critical navigation elements from a website."""
    
    results = {
        "main_nav": [],
        "secondary_nav": [],
        "footer_links": [],
        "search_available": False,
        "sitemap_available": False,
        "sitemap_urls": [],
        "page_title": "",
        "error": None
    }
    
    try:
        # Normalize URL
        if not url.lower().startswith(('http://', 'https://')):
            url = f"https://{url}"
            
        # Get main page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        # Use BeautifulSoup for better HTML parsing
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract page title
        title_tag = soup.find('title')
        results["page_title"] = title_tag.text if title_tag else "No title found"
        
        # Extract primary navigation
        nav_elements = []
        
        # Look for dedicated nav elements first
        for nav in soup.find_all('nav'):
            if len(nav.find_all('a')) > 2:  # Only include navs with multiple links
                nav_elements.append(nav)
        
        # Look for header elements that might contain navigation
        header = soup.find('header')
        if header:
            nav_elements.append(header)
            
        # Look for divs with navigation-related classes
        for div in soup.find_all(['div', 'ul']):
            class_attr = div.get('class', [])
            class_name = ' '.join(class_attr) if class_attr else ''
            if is_navigation_element(div, class_name):
                nav_elements.append(div)
        
        # Process main navigation elements
        primary_nav_processed = False
        for nav in nav_elements:
            links = extract_navigation_links(nav)
            if links and not primary_nav_processed:
                results["main_nav"] = links
                primary_nav_processed = True
            elif links:
                results["secondary_nav"].extend(links)
        
        # Remove duplicates from secondary nav
        if results["secondary_nav"]:
            main_texts = [link["text"].lower() for link in results["main_nav"]]
            results["secondary_nav"] = [link for link in results["secondary_nav"] 
                                     if link["text"].lower() not in main_texts]
        
        # Extract footer links
        footer = soup.find('footer')
        if footer:
            results["footer_links"] = extract_navigation_links(footer)
        
        # Check for search functionality
        search_elements = soup.find_all(['input', 'form'], attrs={
            'type': 'search'
        }) or soup.find_all(['input', 'form'], class_=lambda c: c and 'search' in str(c).lower())
        
        results["search_available"] = len(search_elements) > 0
        
        # Check for sitemap in a separate request
        try:
            sitemap_response = requests.get(f"{url}/sitemap.xml", headers=headers, timeout=5)
            results["sitemap_available"] = sitemap_response.status_code == 200
            
            if results["sitemap_available"]:
                # Parse sitemap URLs
                sitemap_soup = BeautifulSoup(sitemap_response.text, 'xml')
                locations = sitemap_soup.find_all('loc')
                # Limit to first 20 URLs to avoid overwhelming the prompt
                results["sitemap_urls"] = [loc.text for loc in locations[:20]]
        except:
            results["sitemap_available"] = False
            
        return results
        
    except Exception as e:
        results["error"] = str(e)
        return results

def get_navigation_guidance(website_structure, query):
    """
    Uses Gemini AI to find a navigation path based on the website structure and query.
    """
    try:
        if not website_structure:
            return "Please analyze the website structure first."
            
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Format navigation data for the prompt
        main_nav_data = "\n".join([f"- {link['text']} -> {link['url']}" for link in website_structure['main_nav']])
        secondary_nav_data = "\n".join([f"- {link['text']} -> {link['url']}" for link in website_structure['secondary_nav']])
        footer_data = "\n".join([f"- {link['text']} -> {link['url']}" for link in website_structure['footer_links']])
        
        prompt = f"""
# WEBSITE STRUCTURE ANALYSIS
Website Title: {website_structure['page_title']}

## Main Navigation Menu
{main_nav_data if main_nav_data else "No main navigation found"}

## Secondary Navigation Elements
{secondary_nav_data if secondary_nav_data else "No secondary navigation found"}

## Footer Links
{footer_data if footer_data else "No footer links found"}

## Website Features
- Search Functionality: {"Available" if website_structure['search_available'] else "Not Found"}
- Sitemap: {"Available" if website_structure['sitemap_available'] else "Not Found"}

# USER QUERY
The user wants to find information about: "{query}"

# TASK
Generate a step-by-step navigation plan to locate this information on the website.

# OUTPUT FORMAT
Use the following structured format for your response:

NAVIGATION PATH: [Provide the most likely navigation path using > symbols]
SUGGESTED LINKS: [List the 1-3 most relevant links to click]
SEARCH RECOMMENDATION: [Should the user use the search functionality? Yes/No]
CONFIDENCE: [High/Medium/Low - How confident are you in this navigation path?]
RATIONALE: [Brief explanation of why you selected this path]

# EXAMPLE OUTPUT
NAVIGATION PATH: Home > Research > Publications
SUGGESTED LINKS:
- Research -> /research
- Faculty Publications -> /research/publications
SEARCH RECOMMENDATION: Yes, search for "{query}" if navigation path doesn't yield results
CONFIDENCE: Medium
RATIONALE: The query appears to be about research publications, which are typically found under Research section of academic websites.

# IMPORTANT INSTRUCTIONS
- Analyze the available navigation options and determine the most logical path to the information.
- Consider the context and theme of the website when making recommendations.
- If the information appears to be under multiple potential sections, list all relevant options.
- If search functionality is available and the query is specific, recommend using search.
- Be honest about your confidence level.
"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating navigation guidance: {str(e)}"

def generate_selenium_code(user_prompt, website_structure):
    """Generate optimized Selenium code based on website structure"""
    try:
        if not website_structure:
            return "Please analyze the website structure first."
            
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Format navigation data for the prompt
        main_nav_data = "\n".join([f"- {link['text']} -> {link['url']}" for link in website_structure['main_nav']])
        secondary_nav_data = "\n".join([f"- {link['text']} -> {link['url']}" for link in website_structure['secondary_nav']])
        
        # Extract website domain from any URL in the structure
        website_domain = ""
        if website_structure['main_nav'] and 'url' in website_structure['main_nav'][0]:
            url = website_structure['main_nav'][0]['url']
            if url.startswith('http'):
                # Extract domain from full URL
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                website_domain = parsed_url.netloc
            else:
                # Try to extract from the stored website input
                website_parts = re.split(r'[/:]', website_structure.get('website', ''))
                website_domain = next((part for part in website_parts if part and '.' in part), '')
        
        prompt = f"""
# WEBSITE STRUCTURE
Website: {website_domain if website_domain else "Unknown"}
Page Title: {website_structure['page_title']}

## Navigation Elements
Main Navigation:
{main_nav_data if main_nav_data else "No main navigation found"}

Secondary Navigation:
{secondary_nav_data if secondary_nav_data else "No secondary navigation found"}

Search Available: {"Yes" if website_structure['search_available'] else "No"}

# USER REQUEST
"{user_prompt}"

# TASK
Generate a Python Selenium script that will navigate the website and find the requested information.

# INSTRUCTIONS
1. Use the provided website structure to make navigation decisions.
2. Handle both relative and absolute URLs correctly.
3. Include appropriate waits and error handling.
4. If search is available and appropriate for the task, use it.
5. Include detailed comments explaining your approach.
6. Extract and display the relevant information once found.
7. Make the script robust to handle timing issues and element changes.

# SELENIUM SCRIPT REQUIREMENTS
- Use Chrome WebDriver
- Include exception handling for robustness
- Close the browser properly
- Implement explicit waits where needed
- Print helpful status messages during execution
- Extract and display the requested information
"""
        
        response = model.generate_content(prompt)
        generated_code = clean_code_fences(response.text)
        return generated_code
    except Exception as e:
        return f"Error generating Selenium code: {str(e)}\n{traceback.format_exc()}"

# Process sidebar button actions and update conversation history
if analyze_site_button:
    if not search_website.strip():
        st.session_state.messages.append({"role": "assistant", "content": "Please enter a website to analyze."})
    else:
        with st.spinner(f"Analyzing website structure for {search_website}..."):
            structure = analyze_website_structure(search_website.strip())
            if structure.get("error"):
                st.session_state.messages.append({"role": "assistant", "content": f"Error analyzing website: {structure['error']}"})
            else:
                # Store the structure for later use
                structure["website"] = search_website.strip()
                st.session_state.website_structure = structure
                
                # Format a summary message
                main_nav_count = len(structure["main_nav"])
                secondary_nav_count = len(structure["secondary_nav"])
                footer_count = len(structure["footer_links"])
                
                summary = f"""
### Website Structure Analysis: {search_website}

**Title:** {structure["page_title"]}

**Navigation Elements Found:**
- Main Navigation: {main_nav_count} links
- Secondary Navigation: {secondary_nav_count} links
- Footer Links: {footer_count} links

**Features:**
- Search Functionality: {"✅ Available" if structure["search_available"] else "❌ Not Found"}
- Sitemap: {"✅ Available" if structure["sitemap_available"] else "❌ Not Found"}

The website structure has been analyzed and stored. You can now search for specific information or generate navigation paths.
"""
                st.session_state.messages.append({"role": "user", "content": f"Analyze structure of {search_website}"})
                st.session_state.messages.append({"role": "assistant", "content": summary})

if get_navigation_path:
    if not gemini_api_key:
        st.session_state.messages.append({"role": "assistant", "content": "Please enter your Gemini API key."})
    elif not st.session_state.website_structure:
        st.session_state.messages.append({"role": "assistant", "content": "Please analyze a website first."})
    elif not search_query.strip():
        st.session_state.messages.append({"role": "assistant", "content": "Please enter a search query."})
    else:
        with st.spinner(f"Finding navigation path for '{search_query}'..."):
            guidance = get_navigation_guidance(st.session_state.website_structure, search_query.strip())
            st.session_state.messages.append({"role": "user", "content": f"Find navigation path for: {search_query}"})
            st.session_state.messages.append({"role": "assistant", "content": guidance})

if generate_code:
    if not gemini_api_key:
        st.session_state.messages.append({"role": "assistant", "content": "Please enter your Gemini API key."})
    elif not st.session_state.website_structure:
        st.session_state.messages.append({"role": "assistant", "content": "Please analyze a website first."})
    elif not user_prompt.strip():
        st.session_state.messages.append({"role": "assistant", "content": "Please enter a prompt for Selenium automation."})
    else:
        with st.spinner(f"Generating Selenium code for '{user_prompt}'..."):
            code = generate_selenium_code(user_prompt.strip(), st.session_state.website_structure)
            st.session_state.generated_code = code
            
            # Format for display
            st.session_state.messages.append({"role": "user", "content": f"Generate Selenium code for: {user_prompt}"})
            st.session_state.messages.append({"role": "assistant", "content": f"Generated Selenium Code:\n```python\n{code}\n```"})

if execute_code:
    if "generated_code" not in st.session_state:
        st.session_state.messages.append({"role": "assistant", "content": "No Selenium code generated yet. Please generate code first."})
    else:
        try:
            with st.spinner("Executing Selenium code..."):
                # Create a safe execution environment with common imports
                local_namespace = {
                    "requests": requests,
                    "BeautifulSoup": BeautifulSoup,
                    "re": re,
                    "os": os,
                    "traceback": traceback,
                    "concurrent": concurrent.futures
                }
                
                # Need to dynamically import selenium since it may not be installed
                try:
                    from selenium import webdriver
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    from selenium.common.exceptions import TimeoutException, NoSuchElementException
                    
                    local_namespace.update({
                        "webdriver": webdriver,
                        "By": By,
                        "Keys": Keys,
                        "WebDriverWait": WebDriverWait,
                        "EC": EC,
                        "TimeoutException": TimeoutException,
                        "NoSuchElementException": NoSuchElementException
                    })
                except ImportError:
                    st.session_state.messages.append({"role": "assistant", "content": "Error: Selenium is not installed. Please install it with 'pip install selenium'."})
                    st.stop()
                
                # Capture print output
                from io import StringIO
                import sys
                
                old_stdout = sys.stdout
                sys.stdout = mystdout = StringIO()
                
                try:
                    exec(st.session_state.generated_code, local_namespace)
                    execution_output = mystdout.getvalue()
                finally:
                    sys.stdout = old_stdout
                
                st.session_state.messages.append({"role": "assistant", "content": f"Execution Results:\n```\n{execution_output}\n```"})
        except Exception as e:
            error_output = f"Error executing Selenium code: {str(e)}\n\n{traceback.format_exc()}"
            st.session_state.messages.append({"role": "assistant", "content": f"```\n{error_output}\n```"})

# Add a chat input section in the main area
user_chat = st.chat_input("Ask a question about website navigation")
if user_chat:
    st.session_state.messages.append({"role": "user", "content": user_chat})
    
    # Process the user question
    if not gemini_api_key:
        st.session_state.messages.append({"role": "assistant", "content": "Please enter your Gemini API key in the sidebar to enable AI responses."})
    else:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Create a context from the website structure if available
            context = ""
            if st.session_state.website_structure:
                website = st.session_state.website_structure.get("website", "the analyzed website")
                main_nav_count = len(st.session_state.website_structure["main_nav"])
                has_search = st.session_state.website_structure["search_available"]
                
                context = f"""
                The user has analyzed the website '{website}'. 
                This website has {main_nav_count} main navigation links and {"does" if has_search else "does not"} have search functionality.
                """
            
            prompt = f"""
            {context}
            
            User question: {user_chat}
            
            Provide a helpful response about website navigation or information retrieval. If the question is about how to find specific information on a website, suggest relevant approaches. If it's a technical question about the tool's functionality, explain how it works.
            """
            
            response = model.generate_content(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error processing your question: {str(e)}"})

# Display conversation messages using Streamlit's chat message UI
for message in st.session_state.messages:
    if message["role"] == "user":
        st.chat_message("user", avatar="🧑").markdown(message["content"])
    else:
        st.chat_message("assistant", avatar="🤖").markdown(message["content"])

# Add code to enable downloading navigation data as JSON
if st.session_state.website_structure:
    with st.sidebar:
        st.subheader("Export Data")
        
        import json
        
        # Create download button for navigation structure
        if st.download_button(
            label="Download Navigation Data (JSON)",
            data=json.dumps(st.session_state.website_structure, indent=2),
            file_name=f"{st.session_state.website_structure.get('website', 'website')}_navigation.json",
            mime="application/json"
        ):
            st.success("Navigation data downloaded successfully!")