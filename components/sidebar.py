import streamlit as st
import time
import datetime

def render_sidebar():
    """Render the simplified sidebar focused on agent controls."""
    with st.sidebar:
        st.title("AI Web Assistant")
        
        # Create tabs for different sidebar sections
        main_tab, settings_tab = st.tabs(["Main", "Settings"])
        
        with main_tab:
            # API Key status section
            st.subheader("API Key Status")
            if st.session_state.api_key_set:
                st.success("API key loaded successfully")
            else:
                st.error("API key not found")
                st.info("Add OPENAI_API_KEY=your_key to your .env file")
                api_key = st.text_input("Enter API Key", type="password")
                if api_key and st.button("Save API Key"):
                    st.session_state.api_key = api_key
                    st.session_state.api_key_set = True
                    st.rerun()
            
            # Agent task suggestions
            st.subheader("Task Suggestions")
            st.write("Try these example tasks:")
            
            examples = [
                "Find the best deals on iPhones in India",
                "List all video game releases in April 2025",
                "What are the top 5 headlines in tech today?",
                "Compare prices for noise-cancelling headphones",
                "Find cheap hotels in Tokyo for next weekend"
            ]
            
            for example in examples:
                if st.button(example, key=f"example_{hash(example)}"):
                    new_message = {"role": "user", "content": example}
                    st.session_state.messages.append(new_message)
                    st.session_state.conversations[st.session_state.current_conversation_id]["messages"] = st.session_state.messages
                    st.rerun()
            
            # Conversation management section
            st.subheader("Conversations")
            
            # New conversation button for easy chat start
            if st.button("New Conversation", key="new_chat"):
                new_id = f"conversation_{time.strftime('%Y%m%d_%H%M%S')}"
                st.session_state.current_conversation_id = new_id
                st.session_state.conversations[new_id] = {
                    "title": f"Conversation {len(st.session_state.conversations)}",
                    "messages": [
                        {"role": "assistant", "content": "Hello! I'm your AI Web Assistant. I can help you automate web tasks. What would you like to do today?"}
                    ],
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                }
                st.session_state.messages = st.session_state.conversations[new_id]["messages"]
                st.session_state.agent_result = None
                st.rerun()
            
            # Existing conversations select box
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
                    "Select conversation",
                    options=[id for id, _ in conversation_options],
                    format_func=lambda x: next((title for id, title in conversation_options if id == x), x),
                    index=0
                )
                
                if selected_conversation != st.session_state.current_conversation_id:
                    st.session_state.current_conversation_id = selected_conversation
                    st.session_state.messages = st.session_state.conversations[selected_conversation]["messages"]
                    st.rerun()
                    
                # Option to rename the current conversation
                new_title = st.text_input(
                    "Rename conversation",
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
            
            # Help section
            st.subheader("Help & Information")
            with st.expander("About This App"):
                st.markdown("""
                ### AI Web Assistant
                
                This application uses AI to automate web tasks. Simply describe what you want to find or do online, 
                and the assistant will navigate websites for you and return the information you need.
                
                **Examples of tasks you can ask:**
                
                - Find product prices and comparisons
                - Search for news on specific topics
                - Look up information across multiple websites
                - Find travel options and pricing
                - Research topics and compile information
                
                The app uses a headless browser controlled by AI to navigate the web on your behalf.
                """)