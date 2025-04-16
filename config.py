import streamlit as st
import os
import traceback
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("webnavassist")

def set_page_config():
    """Set the page configuration for the app with error handling."""
    try:
        st.set_page_config(
            page_title="AI Web Assistant",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': 'https://github.com/yourusername/aiwebassistant',
                'Report a bug': 'https://github.com/yourusername/aiwebassistant/issues',
                'About': 'AI Web Assistant - Automated web tasks powered by AI.'
            }
        )
        
        logger.info("Page configuration set successfully")
    except Exception as e:
        logger.error(f"Error setting page configuration: {str(e)}")
        st.error(f"Error setting page configuration: {str(e)}")
        st.code(traceback.format_exc())

def load_api_key():
    """Load API key from .env file or Streamlit secrets with robust error handling."""
    api_key = None
    
    try:
        # Try loading from .env file
        logger.info("Attempting to load API key from .env file")
        load_dotenv()
        env_api_key = os.getenv("OPENAI_API_KEY")
        
        if env_api_key:
            logger.info("API key loaded from .env file")
            api_key = env_api_key
        else:
            logger.info("No API key found in .env file, trying Streamlit secrets")
            
            # Try loading from Streamlit secrets
            try:
                api_key = st.secrets["OPENAI_API_KEY"]
                logger.info("API key loaded from Streamlit secrets")
            except Exception as secret_error:
                logger.warning(f"Failed to load API key from Streamlit secrets: {str(secret_error)}")
        
        if not api_key:
            logger.warning("No API key found in either .env file or Streamlit secrets")
            st.warning("No OpenAI API key found. Please add it to your .env file or Streamlit secrets.")
    
    except Exception as e:
        logger.error(f"Error loading API key: {str(e)}")
        st.error(f"Error loading API key: {str(e)}")
        st.code(traceback.format_exc())
    
    # Mask the API key for logging (show only first 3 and last 3 characters)
    if api_key:
        masked_key = api_key[:3] + "..." + api_key[-3:] if len(api_key) > 6 else "***"
        logger.info(f"API key loaded: {masked_key}")
    
    return api_key

def initialize_session_state():
    """Initialize session state variables with error handling."""
    try:
        logger.info("Initializing session state")
        
        # Agent related state
        if 'agent_mode' not in st.session_state:
            st.session_state.agent_mode = True  # Default to agent mode since we're removing navigation
            
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
                {"role": "assistant", "content": "Hello! I'm your AI Web Assistant. I can help you automate web tasks. Just tell me what you're looking for, and I'll navigate the web for you. What would you like to do today?"}
            ]
        
        # Conversation history storage
        if 'conversations' not in st.session_state:
            st.session_state.conversations = {}
        
        if 'current_conversation_id' not in st.session_state:
            st.session_state.current_conversation_id = "default"
            # Initialize default conversation
            if "default" not in st.session_state.conversations:
                st.session_state.conversations["default"] = {
                    "title": "New chat",
                    "messages": st.session_state.messages.copy(),
                    "timestamp": ""
                }
                
        # Set API key if available
        api_key = load_api_key()
        if api_key:
            st.session_state.api_key = api_key
            st.session_state.api_key_set = True
            
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