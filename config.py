import streamlit as st
import os
import traceback
import logging
from dotenv import load_dotenv
import re

# Set up logging with enhanced level
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("webnavassist")

def set_page_config():
    """Set the page configuration for the app with error handling."""
    try:
        st.set_page_config(
            page_title="Website Analyzer",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': 'https://github.com/yourusername/websiteanalyzer',
                'Report a bug': 'https://github.com/yourusername/websiteanalyzer/issues',
                'About': 'Website Analyzer - Automated website analysis powered by AI.'
            }
        )
        
        logger.info("Page configuration set successfully")
    except Exception as e:
        logger.error(f"Error setting page configuration: {str(e)}")
        st.error(f"Error setting page configuration: {str(e)}")
        st.code(traceback.format_exc())

def validate_api_key(api_key):
    """Validate API key format and structure."""
    if not api_key:
        return False, "API key is empty"
    
    # Remove any whitespace
    api_key = api_key.strip()
    
    # Basic validation - OpenAI keys usually start with 'sk-' and are longer than 30 chars
    if not api_key.startswith('sk-'):
        return False, "API key should start with 'sk-'"
    
    if len(api_key) < 30:
        return False, "API key appears too short"
    
    # Check for invalid characters
    if re.search(r'[^a-zA-Z0-9_\-]', api_key):
        return False, "API key contains invalid characters"
        
    return True, "Valid API key format"

def load_api_key():
    """Load API key from .env file or Streamlit secrets with robust error handling."""
    api_key = None
    
    try:
        # Try loading from .env file
        logger.info("Attempting to load API key from .env file")
        load_dotenv()
        env_api_key = os.getenv("OPENAI_API_KEY")
        
        if env_api_key:
            # Validate the key
            is_valid, message = validate_api_key(env_api_key)
            if is_valid:
                logger.info(f"API key loaded from .env file: {message}")
                api_key = env_api_key.strip()  # Remove any whitespace
            else:
                logger.warning(f"API key from .env file appears invalid: {message}")
        else:
            logger.info("No API key found in .env file, trying Streamlit secrets")
            
            # Try loading from Streamlit secrets
            try:
                secret_api_key = st.secrets.get("OPENAI_API_KEY")
                if secret_api_key:
                    # Validate the key
                    is_valid, message = validate_api_key(secret_api_key)
                    if is_valid:
                        logger.info(f"API key loaded from Streamlit secrets: {message}")
                        api_key = secret_api_key.strip()  # Remove any whitespace
                    else:
                        logger.warning(f"API key from Streamlit secrets appears invalid: {message}")
                else:
                    logger.warning("No API key found in Streamlit secrets")
            except Exception as secret_error:
                logger.warning(f"Failed to load API key from Streamlit secrets: {str(secret_error)}")
        
        if not api_key:
            logger.warning("No valid API key found in either .env file or Streamlit secrets")
            st.warning("No OpenAI API key found or the key is invalid. Please add a valid key to your .env file or Streamlit secrets.")
    
    except Exception as e:
        logger.error(f"Error loading API key: {str(e)}")
        st.error(f"Error loading API key: {str(e)}")
        st.code(traceback.format_exc())
    
    return api_key

def initialize_session_state():
    """Initialize session state variables with error handling."""
    try:
        logger.info("Initializing session state")
        
        # Website analysis related state
        if 'website_analyzed' not in st.session_state:
            st.session_state.website_analyzed = False
            
        if 'website_url' not in st.session_state:
            st.session_state.website_url = None
            
        if 'site_data' not in st.session_state:
            st.session_state.site_data = None
        
        # Agent related state
        if 'agent_mode' not in st.session_state:
            st.session_state.agent_mode = True
            
        if 'agent_result' not in st.session_state:
            st.session_state.agent_result = None
        
        # API key related state
        if 'api_key' not in st.session_state:
            st.session_state.api_key = None
            
        if 'api_key_set' not in st.session_state:
            st.session_state.api_key_set = False
        
        # Browser settings
        if 'headless' not in st.session_state:
            st.session_state.headless = True
            
        if 'browser_width' not in st.session_state:
            st.session_state.browser_width = 1280
            
        if 'browser_height' not in st.session_state:
            st.session_state.browser_height = 800
        
        # Chat interface related state
        if 'messages' not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! I'm your Website Analyzer. I can help you analyze any website and find information for you. Please enter a website URL to get started."}
            ]
        
        # Conversation history storage
        if 'conversations' not in st.session_state:
            st.session_state.conversations = {}
        
        if 'current_conversation_id' not in st.session_state:
            st.session_state.current_conversation_id = "default"
            # Initialize default conversation
            if "default" not in st.session_state.conversations:
                st.session_state.conversations["default"] = {
                    "title": "New analysis",
                    "messages": st.session_state.messages.copy(),
                    "timestamp": ""
                }
        
        # Load and set API key if available
        api_key = load_api_key()
        if api_key:
            st.session_state.api_key = api_key
            st.session_state.api_key_set = True
            # Also set it in the environment for good measure
            os.environ["OPENAI_API_KEY"] = api_key
            logger.debug("API key set in environment variable from session state")
        else:
            st.session_state.api_key_set = False
            
        logger.info("Session state initialized successfully")
            
    except Exception as e:
        logger.error(f"Error initializing session state: {str(e)}")
        st.error(f"Error initializing session state: {str(e)}")
        st.code(traceback.format_exc())
        
        # Try to provide a minimal fallback state
        if 'messages' not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! I'm experiencing some initialization issues. Please check the error message above and try refreshing the page."}
            ]
            
        if 'api_key_set' not in st.session_state:
            st.session_state.api_key_set = False