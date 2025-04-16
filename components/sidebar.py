import streamlit as st
import time
import datetime
import logging
import os
import re

logger = logging.getLogger("sidebar")

def is_valid_openai_key(api_key):
    """Validate if the API key has the correct format."""
    if not api_key:
        return False, "API key is empty"
    
    # Remove any whitespace
    api_key = api_key.strip()
    
    # Basic validation - OpenAI keys usually start with 'sk-' and are longer than 30 chars
    if not api_key.startswith('sk-'):
        return False, "API key should start with 'sk-'"
    
    if len(api_key) < 30:
        return False, "API key is too short"
    
    # Check for invalid characters
    if re.search(r'[^a-zA-Z0-9_\-]', api_key):
        return False, "API key contains invalid characters"
        
    return True, "Valid API key format"

def render_sidebar():
    """Render the sidebar with website analysis settings."""
    with st.sidebar:
        st.title("Website Analyzer")
        
        # Create tabs for different sidebar sections
        main_tab, settings_tab = st.tabs(["Main", "Settings"])
        
        with main_tab:
            # API Key status section with enhanced validation
            st.subheader("API Key Status")
            
            # Check if API key is in session state and validate it
            current_key_valid = False
            if st.session_state.get('api_key_set', False) and st.session_state.get('api_key'):
                is_valid, message = is_valid_openai_key(st.session_state.api_key)
                if is_valid:
                    st.success("API key loaded successfully")
                    current_key_valid = True
                else:
                    st.error(f"Stored API key is invalid: {message}")
                    st.session_state.api_key_set = False
            
            if not current_key_valid:
                st.error("Valid API key not found")
                st.info("Add a valid OpenAI API key below")
                
                # Expanded API key input with validation feedback
                with st.form("api_key_form"):
                    api_key = st.text_input("Enter OpenAI API Key", type="password", 
                                        help="Your key should start with 'sk-'")
                    submit_key = st.form_submit_button("Save API Key")
                    
                    if submit_key:
                        if api_key:
                            # Validate the key format
                            is_valid, message = is_valid_openai_key(api_key)
                            
                            if is_valid:
                                # Clean the key (remove whitespace)
                                clean_api_key = api_key.strip()
                                
                                # Update session state
                                st.session_state.api_key = clean_api_key
                                st.session_state.api_key_set = True
                                
                                # Set environment variable for good measure
                                os.environ["OPENAI_API_KEY"] = clean_api_key
                                
                                
                                st.success("API key saved successfully!")
                                st.rerun()
                            else:
                                st.error(f"Invalid API key: {message}")
                        else:
                            st.error("Please enter an API key")
                
                # Add a note about how to get an API key
                st.info("You need an OpenAI API key to use this app. Get one at: https://platform.openai.com/api-keys")
            
            # Only show task suggestions if a website is being analyzed
            if st.session_state.get('website_analyzed', False) and st.session_state.get('site_data'):
                site_title = st.session_state.site_data.get('title', 'this website')
                base_url = st.session_state.website_url
                
                # Website info
                st.subheader("Current Website")
                st.write(f"**Analyzing:** {site_title}")
                st.write(f"**URL:** {base_url}")
                
                # Task suggestions
                st.subheader("Task Suggestions")
                st.write("Try these examples:")
                
                # Dynamic examples based on the current website
                if st.session_state.site_data.get('navigation_links'):
                    # Extract main navigation sections
                    nav_sections = {}
                    for link in st.session_state.site_data['navigation_links']:
                        section = link.get('section', 'Main Navigation')
                        if section not in nav_sections:
                            nav_sections[section] = []
                        nav_sections[section].append(link)
                    
                    # Generate examples based on navigation
                    examples = []
                    for section, links in nav_sections.items():
                        if links:
                            # Use first link in each section for examples
                            link_text = links[0]['text']
                            examples.append(f"Find information about {link_text}")
                    
                    # Add form-related examples if forms are detected
                    if st.session_state.site_data.get('forms'):
                        form_purposes = {form.get('purpose', 'unknown') for form in st.session_state.site_data['forms']}
                        for purpose in form_purposes:
                            if purpose not in ('unknown', 'search'):
                                examples.append(f"How do I {purpose} on {site_title}?")
                            elif purpose == 'search':
                                examples.append(f"How can I search on {site_title}?")
                    
                    # Add social media related examples if social links detected
                    if st.session_state.site_data.get('social_links'):
                        examples.append(f"What social media profiles does {site_title} have?")
                    
                    # Add more general examples
                    examples.extend([
                        f"What are the main topics covered on {site_title}?",
                        f"Find contact information on {site_title}",
                        f"What products or services does {site_title} offer?",
                        f"Search for pricing information on {site_title}"
                    ])
                else:
                    # Generic examples if no navigation found
                    examples = [
                        f"What is {site_title} about?",
                        f"Find the main sections of {site_title}",
                        f"What contact information is available?",
                        f"Find information about products or services",
                        f"Look for pricing or cost information"
                    ]
                
                # Display example buttons (limit to 5)
                for example in examples[:5]:
                    if st.button(example, key=f"example_{hash(example)}"):
                        new_message = {"role": "user", "content": example}
                        st.session_state.messages.append(new_message)
                        st.session_state.conversations[st.session_state.current_conversation_id]["messages"] = st.session_state.messages
                        st.rerun()
            
            # Conversation management section
            st.subheader("Analyses History")
            
            # New conversation button for easy chat start
            if st.button("New Website Analysis", key="new_analysis"):
                # Reset website analysis state
                st.session_state.website_analyzed = False
                st.session_state.website_url = None
                st.session_state.site_data = None
                
                # Create new conversation
                new_id = f"conversation_{time.strftime('%Y%m%d_%H%M%S')}"
                st.session_state.current_conversation_id = new_id
                st.session_state.conversations[new_id] = {
                    "title": "New Website Analysis",
                    "messages": [
                        {"role": "assistant", "content": "Hello! I'm your Website Analyzer. I can help you analyze any website and find information for you. Please enter a website URL to get started."}
                    ],
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                }
                st.session_state.messages = st.session_state.conversations[new_id]["messages"]
                st.session_state.agent_result = None
                st.rerun()
            
            # Previous analyses select box
            conversation_options = []
            for conv_id, data in reversed(list(st.session_state.conversations.items())):
                title_display = data['title']
                if "timestamp" in data and data["timestamp"]:
                    try:
                        date_obj = datetime.datetime.strptime(data["timestamp"], '%Y-%m-%d %H:%M:%S')
                        date_display = date_obj.strftime('%b %d')
                        title_display = f"{data['title']} ({date_display})"
                    except Exception:
                        pass
                conversation_options.append((conv_id, title_display))
            
            if conversation_options:
                selected_conversation = st.selectbox(
                    "Previous analyses",
                    options=[id for id, _ in conversation_options],
                    format_func=lambda x: next((title for id, title in conversation_options if id == x), x),
                    index=0
                )
                
                if selected_conversation != st.session_state.current_conversation_id:
                    # Load the selected conversation
                    st.session_state.current_conversation_id = selected_conversation
                    st.session_state.messages = st.session_state.conversations[selected_conversation]["messages"]
                    
                    # Restore website URL and analyzed state if available
                    if "url" in st.session_state.conversations[selected_conversation]:
                        st.session_state.website_url = st.session_state.conversations[selected_conversation]["url"]
                        st.session_state.website_analyzed = True
                    else:
                        # If this is an old conversation without URL info, reset analysis state
                        st.session_state.website_analyzed = False
                        st.session_state.website_url = None
                        st.session_state.site_data = None
                    
                    st.rerun()
                    
                # Option to rename the current conversation
                new_title = st.text_input(
                    "Rename analysis",
                    value=st.session_state.conversations[st.session_state.current_conversation_id]["title"]
                )
                if new_title != st.session_state.conversations[st.session_state.current_conversation_id]["title"]:
                    st.session_state.conversations[st.session_state.current_conversation_id]["title"] = new_title
        
        # Settings tab
        with settings_tab:
            st.subheader("Browser Settings")
            
            # Headless mode option
            headless = st.checkbox("Headless Mode", value=True, help="Run browser in headless mode (no visible window)")
            if headless != st.session_state.get('headless', True):
                st.session_state.headless = headless
            
            # Advanced options expandable section
            with st.expander("Advanced Options"):
                # Browser window size
                st.subheader("Browser Window Size")
                col1, col2 = st.columns(2)
                with col1:
                    width = st.number_input("Width", min_value=800, max_value=3840, value=1280, step=10)
                with col2:
                    height = st.number_input("Height", min_value=600, max_value=2160, value=800, step=10)
                
                # Set browser dimensions in session state
                if width != st.session_state.get('browser_width', 1280) or height != st.session_state.get('browser_height', 800):
                    st.session_state.browser_width = width
                    st.session_state.browser_height = height
                
                # Wait time settings
                st.subheader("Timing Settings")
                wait_time = st.slider("Page Load Wait Time (seconds)", min_value=1, max_value=30, value=10)
                if wait_time != st.session_state.get('wait_time', 10):
                    st.session_state.wait_time = wait_time
                    
                # Sitemap settings
                st.subheader("Sitemap Settings")
                max_depth = st.slider("Maximum Crawl Depth", min_value=1, max_value=5, value=3, 
                                     help="Controls how deep the crawler will go into the website structure. Higher values mean more comprehensive analysis but longer crawl times.")
                if max_depth != st.session_state.get('max_depth', 3):
                    st.session_state.max_depth = max_depth
                
                # Request rate limiting (new)
                st.subheader("Rate Limiting")
                requests_per_minute = st.slider("Requests Per Minute", min_value=10, max_value=120, value=30,
                                              help="Limits how many requests are made per minute to avoid overloading websites. Higher values mean faster analysis but might trigger rate limiting.")
                if requests_per_minute != st.session_state.get('requests_per_minute', 30):
                    st.session_state.requests_per_minute = requests_per_minute
                
                # Max pages to crawl (new)
                max_pages = st.slider("Maximum Pages", min_value=10, max_value=200, value=50,
                                     help="Maximum number of pages to analyze. Higher values provide more comprehensive analysis but take longer.")
                if max_pages != st.session_state.get('max_pages', 50):
                    st.session_state.max_pages = max_pages
                
                st.info("⚠️ Setting higher depth values or maximum pages will increase crawl time significantly. For large websites, moderate values are recommended.")
                
                # API model settings (new)
                st.subheader("API Settings")
                model_name = st.selectbox(
                    "OpenAI Model", 
                    options=["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
                    index=0,
                    help="Select which OpenAI model to use. GPT-4o is recommended but may cost more."
                )
                if model_name != st.session_state.get('model_name', "gpt-4o"):
                    st.session_state.model_name = model_name
                    logger.debug(f"Changed model to: {model_name}")
                
                # Debugging section
                st.subheader("Debugging")
                if st.button("Check OpenAI API Connection"):
                    try:
                        from langchain_openai import ChatOpenAI
                        
                        # Get current API key
                        api_key = st.session_state.get('api_key')
                        if not api_key:
                            api_key = os.getenv("OPENAI_API_KEY")
                        
                        if not api_key:
                            st.error("No API key found to test")
                        else:
                            # Test API connection
                            with st.spinner("Testing API connection..."):
                                try:
                                    # First set the key in environment
                                    os.environ["OPENAI_API_KEY"] = api_key
                                    
                                    # Initialize the model
                                    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
                                    
                                    # Test with a simple query
                                    _ = llm.invoke("Hello")
                                    
                                    st.success("✅ API connection successful!")
                                except Exception as e:
                                    st.error(f"❌ API connection failed: {str(e)}")
                                    st.code(str(e))
                    except Exception as e:
                        st.error(f"Error testing API: {str(e)}")
            
            # Help section
            st.subheader("Help & Information")
            with st.expander("About This App"):
                st.markdown("""
                ### Website Analyzer
                
                This application uses AI to analyze websites and find information. The process works in two steps:
                
                1. First, enter a website URL to analyze. The app will generate a detailed sitemap and structure analysis.
                2. Then, ask specific questions about the website content.
                
                **Enhanced Features:**
                
                - **Comprehensive Website Mapping**: Extracts navigation, content sections, forms, and social media links
                - **Intelligent Content Analysis**: Identifies key topics and main content areas
                - **Form Detection**: Recognizes different types of forms like contact, login, or search
                - **Social Media Integration**: Detects social profiles linked from the website
                
                **Examples of what you can ask:**
                
                - Find pricing information on a product or service
                - Locate contact information or support options
                - Extract key information from specific sections
                - Find documentation or help resources
                - Research company information or policies
                - How to interact with forms on the website
                - Find social media profiles
                
                The app uses a headless browser controlled by AI to navigate the website on your behalf.
                """)