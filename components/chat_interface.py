import streamlit as st
import logging
import traceback

# Import services
from services.agent_service import run_agent_task

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
        
        # Chat Input
        try:
            placeholder_text = "Enter a task for the web assistant..."
                
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
                
                result = run_agent_task(
                    user_input, 
                    api_key=st.session_state.api_key,
                    headless=headless,
                    browser_width=browser_width,
                    browser_height=browser_height
                )
                
                # Store result in session state
                st.session_state.agent_result = result
                
                # Generate response message
                response = f"✅ I've completed your request: \"{user_input}\"\n\n"
                
                # Add a summary of the result (limited to avoid huge messages)
                # Extract first 500 characters for the chat
                result_preview = result[:500] + "..." if len(result) > 500 else result
                response += f"**Summary of findings:**\n\n{result_preview}\n\n"
                
                if len(result) > 500:
                    response += "_Full results are available in the expandable section above._"
                
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
                error_message = f"❌ I encountered an error while trying to complete your request: \"{user_input}\"\n\n"
                error_message += f"Error: {str(agent_error)}\n\n"
                error_message += "Please try again with a different query or check if your API key has the correct permissions."
                
                st.markdown(error_message)
                
                # Add error message to chat history
                st.session_state.messages.append({"role": "assistant", "content": error_message})
    
    except Exception as e:
        logger.error(f"Unexpected error in agent processing: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Add error message to chat history
        error_message = f"❌ An unexpected error occurred: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": error_message})