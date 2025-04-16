import streamlit as st
import logging
import traceback
import time

# Import services
from services.agent_service import run_agent_task
# Remove import of generate_system_prompt from sitemap_service
from services.sitemap_service import generate_sitemap
# Import prompts.py functions
from services.prompts import generate_system_prompt, generate_website_analyzed_message, generate_task_prompt
from components.url_input import render_url_input
from components.sitemap_display import display_sitemap
from components.query_mapping_display import display_query_mapping

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("chat_interface")

def render_chat_interface():
    """Render the main chat interface using Streamlit components."""
    try:
        # Display warning if API key not set
        if not st.session_state.api_key_set:
            st.warning("⚠️ OpenAI API key not set. Please add your API key in the sidebar.")
        
        st.subheader("🤖 AI Web Assistant")
        
        # Initialize website analysis state if not present
        if 'website_analyzed' not in st.session_state:
            st.session_state.website_analyzed = False
            
        if 'website_url' not in st.session_state:
            st.session_state.website_url = None
            
        if 'site_data' not in st.session_state:
            st.session_state.site_data = None
            
        # Step 1: URL Input (if not already analyzed)
        if not st.session_state.website_analyzed:
            url = render_url_input()
            
            if url:
                with st.spinner("Analyzing website... This may take a moment..."):
                    # Generate sitemap
                    try:
                        # Get max depth setting from session state
                        max_depth = st.session_state.get('max_depth', 3)
                        
                        st.info(f"Crawling website with depth limit {max_depth}. This may take a few minutes for larger sites.")
                        
                        # Generate sitemap using the new WebsiteSitemapExtractor
                        site_data = generate_sitemap(
                            url=url,
                            max_depth=max_depth
                        )
                        
                        # Store site data and URL in session state
                        st.session_state.site_data = site_data
                        st.session_state.website_url = url
                        st.session_state.website_analyzed = True
                        
                        # Generate welcome message with site info
                        welcome_message = f"✅ Successfully analyzed website: {site_data['title']} ({url})\n\n"
                        
                        # Add information about the sitemap
                        welcome_message += f"I've mapped the structure of this website and found {site_data['internal_link_count']} internal links"
                        if 'external_link_count' in site_data:
                            welcome_message += f" and {site_data['external_link_count']} external links"
                        welcome_message += ".\n\n"
                        
                        # Add information about content sections if available
                        if 'content_sections' in site_data and site_data['content_sections']:
                            welcome_message += f"I've identified {len(site_data['content_sections'])} main content sections.\n\n"
                        
                        # Add information about forms if available
                        if 'forms' in site_data and site_data['forms']:
                            form_types = {form.get('purpose', 'unknown') for form in site_data['forms']}
                            welcome_message += f"The site contains {len(site_data['forms'])} forms including: {', '.join(form_types)}.\n\n"
                        
                        # Add information about social links if available
                        if 'social_links' in site_data and site_data['social_links']:
                            platforms = {link.get('platform', 'unknown') for link in site_data['social_links']}
                            welcome_message += f"I found social media links for: {', '.join(platforms)}.\n\n"
                        
                        welcome_message += "You can now ask me about any specific information you'd like to find on this website."
                        
                        # Reset chat history with new welcome message
                        st.session_state.messages = [
                            {"role": "assistant", "content": welcome_message}
                        ]
                        
                        # Update conversation
                        if 'current_conversation_id' in st.session_state and 'conversations' in st.session_state:
                            conversation_id = st.session_state.current_conversation_id
                            if conversation_id in st.session_state.conversations:
                                st.session_state.conversations[conversation_id]["messages"] = st.session_state.messages
                                st.session_state.conversations[conversation_id]["title"] = f"Analysis of {site_data['title']}"
                                st.session_state.conversations[conversation_id]["timestamp"] = time.strftime('%Y-%m-%d %H:%M:%S')
                                st.session_state.conversations[conversation_id]["url"] = url
                        
                        # Force page refresh to show sitemap
                        st.rerun()
                        
                    except Exception as e:
                        logger.error(f"Error generating sitemap: {str(e)}")
                        st.error(f"Error analyzing website: {str(e)}")
                        st.code(traceback.format_exc())
            
            # If no URL is input yet, show only an empty state and return
            if not st.session_state.website_analyzed:
                st.info("Enter a website URL above to get started.")
                return
        
        # Website has been analyzed at this point
        # Display site information
        if st.session_state.website_analyzed and st.session_state.site_data:
            with st.expander("Website Structure", expanded=False):
                display_sitemap(st.session_state.site_data)
                
            # Display a reset button to analyze a different website
            if st.button("Analyze a Different Website"):
                st.session_state.website_analyzed = False
                st.session_state.website_url = None
                st.session_state.site_data = None
                
                # Start a new conversation
                new_id = f"conversation_{time.strftime('%Y%m%d_%H%M%S')}"
                st.session_state.current_conversation_id = new_id
                st.session_state.conversations[new_id] = {
                    "title": "New Website Analysis",
                    "messages": [
                        {"role": "assistant", "content": "I'm ready to analyze a new website. Please enter a URL to get started."}
                    ],
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                }
                st.session_state.messages = st.session_state.conversations[new_id]["messages"]
                st.session_state.agent_result = None
                st.rerun()
        
        # Agent Results display
        if st.session_state.agent_result:
            with st.expander("Last Task Results", expanded=True):
                st.markdown("**Results from your last request:**")
                st.markdown(st.session_state.agent_result)
        
        # Chat Messages Display
        st.subheader("Conversation")
        chat_container = st.container()
        with chat_container:
            try:
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
            except Exception as message_error:
                logger.error(f"Error displaying messages: {str(message_error)}")
                st.error(f"Error displaying chat history: {str(message_error)}")
                st.session_state.messages = [
                    {"role": "assistant", "content": "Hello! I'm your AI Web Assistant. How can I help you today?"}
                ]
        
        # Chat Input (only if website is analyzed)
        if st.session_state.website_analyzed:
            try:
                placeholder_text = f"Ask about {st.session_state.site_data['title']}..."
                    
                # Process user input
                if user_input := st.chat_input(placeholder_text):
                    # Add user message to chat history
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                    # Update conversation history
                    if 'current_conversation_id' in st.session_state and 'conversations' in st.session_state:
                        conversation_id = st.session_state.current_conversation_id
                        if conversation_id in st.session_state.conversations:
                            st.session_state.conversations[conversation_id]["messages"] = st.session_state.messages
                    
                    # Display user message
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    
                    # Show query mapping analysis before processing
                    with st.expander("Query Mapping Analysis", expanded=False):
                        display_query_mapping(user_input, st.session_state.site_data)
                    
                    # Process the input with agent
                    with st.spinner("Working on your request... This may take a moment."):
                        _process_agent_input(user_input)
                    
                    # Ensure we update the UI
                    st.rerun()
            except Exception as input_error:
                logger.error(f"Error processing user input: {str(input_error)}")
                st.error(f"Error processing your message: {str(input_error)}")
    
    except Exception as e:
        logger.error(f"Critical error in chat interface: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Critical error in chat interface: {str(e)}")
        st.code(traceback.format_exc())
        
        if st.button("Reset Application"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

def _process_agent_input(user_input):
    """Process user input with the web agent."""
    try:
        # Display thinking message
        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("🤔 I'm processing your request...\n\nThis may take a moment while I navigate the web.")
            
            # Run the agent task
            try:
                # Get browser settings from session state
                headless = st.session_state.get('headless', True)
                browser_width = st.session_state.get('browser_width', 1280)
                browser_height = st.session_state.get('browser_height', 800)
                
                # Generate system prompt from site data
                system_prompt = generate_system_prompt(st.session_state.site_data)
                
                # Generate task-specific prompt based on user input
                task_prompt = generate_task_prompt(user_input, st.session_state.site_data)
                
                # Combine prompts
                combined_prompt = f"{system_prompt}\n\n{task_prompt}"
                
                # Run agent with combined prompt and base URL
                result = run_agent_task(
                    task=combined_prompt,
                    base_url=st.session_state.website_url,
                    api_key=st.session_state.api_key,
                    headless=headless,
                    browser_width=browser_width,
                    browser_height=browser_height
                )
                
                # Ensure the result is a string
                if result is None:
                    result = "No results returned from the agent."
                elif not isinstance(result, str):
                    logger.warning(f"Agent returned non-string result of type: {type(result)}")
                    result = str(result)
                
                # Store result in session state
                st.session_state.agent_result = result
                
                # Generate response message
                response = f"✅ I've found information about \"{user_input}\" on {st.session_state.website_url}\n\n"
                
                # Safely extract a preview of the result
                try:
                    # Extract first 500 characters for the chat
                    if len(result) > 500:
                        result_preview = result[:500] + "..."
                    else:
                        result_preview = result
                    
                    response += f"**Summary of findings:**\n\n{result_preview}\n\n"
                    
                    if len(result) > 500:
                        response += "_Full results are available in the expandable section above._"
                except Exception as preview_error:
                    logger.error(f"Error creating result preview: {str(preview_error)}")
                    response += "**Findings:** I completed the search successfully. View the full results in the expandable section above."
                
                # Remove thinking message and show final response
                thinking_placeholder.empty()
                st.markdown(response)
                
                # Add assistant message to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            except Exception as agent_error:
                logger.error(f"Error running agent task: {str(agent_error)}")
                logger.error(traceback.format_exc())
                
                # Remove thinking message and show error
                thinking_placeholder.empty()
                error_message = f"❌ I encountered an error while searching for \"{user_input}\" on {st.session_state.website_url}\n\n"
                error_message += f"Error: {str(agent_error)}\n\n"
                error_message += "Please try a different query or check if your API key has the correct permissions."
                
                st.markdown(error_message)
                
                # Add error message to chat history
                st.session_state.messages.append({"role": "assistant", "content": error_message})
    
    except Exception as e:
        logger.error(f"Unexpected error in agent processing: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Add error message to chat history
        error_message = f"❌ An unexpected error occurred: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": error_message})