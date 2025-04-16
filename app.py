import streamlit as st
import traceback
import sys
import os
from dotenv import load_dotenv

# Import configurations and utilities
from config import initialize_session_state, set_page_config, load_api_key
from components.sidebar import render_sidebar
from components.chat_interface import render_chat_interface

def main():
    """Main application function with error handling."""
    try:
        # Set page configuration
        set_page_config()
        
        # Initialize session state
        initialize_session_state()
        
        # Load API keys
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            st.session_state.api_key = api_key
            st.session_state.api_key_set = True
        else:
            st.session_state.api_key_set = False
        
        # Simple CSS for better spacing and UI enhancements
        st.markdown("""
        <style>
            .stChatFloatingInputContainer {
                padding-bottom: 60px;
            }
            .main .block-container {
                padding-bottom: 100px;
            }
            /* For agent results display */
            .agent-results {
                background-color: rgba(100, 149, 237, 0.1);
                border-left: 3px solid #6495ED;
                padding: 10px;
                margin: 10px 0;
            }
        </style>
        """, unsafe_allow_html=True)

        # Render sidebar
        render_sidebar()

        # Render main chat interface
        container = st.container()
        with container:
            render_chat_interface()
    
    except Exception as e:
        st.error(f"An error occurred in the main() function.")
        st.error(str(e))
        st.code(traceback.format_exc())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("Critical application error")
        st.error(str(e))
        st.code(traceback.format_exc())
        
        # System information for debugging
        st.subheader("System Information")
        st.json({
            "Python Version": sys.version,
            "Python Path": sys.executable,
            "Working Directory": sys.path
        })