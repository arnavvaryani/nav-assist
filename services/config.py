"""
config.py
Configuration utilities for Nav Assist.
"""

import os
from typing import Tuple, Optional, Callable, Any, Dict
import re
import logging

import streamlit as st
from dotenv import load_dotenv

# Load environment variables once at startup
load_dotenv()

logger = logging.getLogger(__name__)

# Constants for validation
OPENAI_PREFIX = "sk-"
DEFAULT_MIN_LENGTH = 30

def set_page_config() -> None:
    """Set the Streamlit page configuration."""
    try:
        st.set_page_config(
            page_title="Nav Assist",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': 'https://github.com/yourusername/websiteanalyzer',
                'Report a bug': 'https://github.com/yourusername/websiteanalyzer/issues',
                'About': 'Nav Assist - Automated website analysis powered by AI.'
            }
        )
        logger.info("Page configuration set successfully")
    except Exception as e:
        logger.error(f"Error setting page configuration: {e}")
        st.error(f"Error setting page configuration: {e}")
        st.code(str(e))

def validate_key(
    key: str,
    *,
    name: str,
    prefix: Optional[str] = None,
    min_length: int = DEFAULT_MIN_LENGTH
) -> Tuple[bool, str]:
    """
    Generic API key validator.
    """
    if not key:
        return False, f"{name} is empty"
    key = key.strip()
    if prefix and not key.startswith(prefix):
        return False, f"{name} should start with '{prefix}'"
    if len(key) < min_length:
        return False, f"{name} appears too short"
    if re.search(r'[^A-Za-z0-9_-]', key):
        return False, f"{name} contains invalid characters"
    return True, "Valid format"

def load_key(
    env_var: str,
    secret_key: str,
    validator: Callable[[str], Tuple[bool, str]]
) -> Optional[str]:
    """
    Load an API key from the environment or Streamlit secrets.
    """
    # Try environment variable
    raw = os.getenv(env_var)
    if raw:
        valid, msg = validator(raw)
        if valid:
            logger.info(f"{env_var} loaded from environment: {msg}")
            return raw.strip()
        else:
            logger.warning(f"{env_var} invalid in environment: {msg}")

    # Fallback to Streamlit secrets
    try:
        secret = st.secrets.get(secret_key)
    except Exception as e:
        logger.warning(f"Failed to access Streamlit secrets for {secret_key}: {e}")
        secret = None

    if secret:
        valid, msg = validator(secret)
        if valid:
            logger.info(f"{secret_key} loaded from Streamlit secrets: {msg}")
            return secret.strip()
        else:
            logger.warning(f"{secret_key} invalid in secrets: {msg}")

    logger.warning(f"No valid {env_var}/{secret_key} found")
    return None

def load_api_key() -> Optional[str]:
    """Load the OpenAI API key."""
    return load_key(
        env_var="OPENAI_API_KEY",
        secret_key="OPENAI_API_KEY",
        validator=lambda k: validate_key(k, name="OpenAI API key", prefix=OPENAI_PREFIX)
    )

def load_langsmith_key() -> Optional[str]:
    """Load the LangSmith API key."""
    return load_key(
        env_var="LANGSMITH_API_KEY",
        secret_key="LANGSMITH_API_KEY",
        validator=lambda k: validate_key(k, name="LangSmith API key")
    )

def initialize_session_state() -> None:
    """Initialize Streamlit session_state with defaults."""
    defaults: Dict[str, Any] = {
        'website_analyzed': False,
        'website_url': None,
        'site_data': None,
        'agent_mode': True,
        'agent_result': None,
        'api_key': None,
        'api_key_set': False,
        'langsmith_api_key': None,
        'langsmith_enabled': False,
        'langsmith_project': "nav-assist",
        'headless': True,
        'browser_width': 1280,
        'browser_height': 800,
        'messages': [
            {"role": "assistant", "content":
             "Hello! I'm your Nav Assist. Enter a website URL to get started."}
        ],
        'conversations': {},
        'current_conversation_id': "default"
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Ensure default conversation exists
    cid = st.session_state.current_conversation_id
    if cid not in st.session_state.conversations:
        st.session_state.conversations[cid] = {
            "title": "New analysis",
            "messages": st.session_state.messages.copy(),
            "timestamp": ""
        }

    # Load and set API keys
    api_key = load_api_key()
    if api_key:
        st.session_state.api_key = api_key
        st.session_state.api_key_set = True
        os.environ["OPENAI_API_KEY"] = api_key

    ls_key = load_langsmith_key()
    if ls_key:
        st.session_state.langsmith_api_key = ls_key
        st.session_state.langsmith_enabled = True
        os.environ["LANGSMITH_API_KEY"] = ls_key
        os.environ["LANGSMITH_PROJECT"] = st.session_state.langsmith_project

    logger.info("Session state initialized")
