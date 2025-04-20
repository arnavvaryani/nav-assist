import asyncio
import streamlit as st
import logging
import traceback
import time
import urllib.parse

# Import services
from services.agent_service import run_agent_task
from services.website_sitemap_extractor import generate_sitemap
from services.prompt_service import generate_system_prompt, generate_website_analyzed_message

# UI components
from components.url_input import render_url_input
from components.sitemap_display import display_sitemap

# Secure query‑mapping (AI‑only)
from components.security_breach_exception import (
    display_query_mapping,
    _find_relevant_pages_with_ai,
    SecurityBreachException
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chat_interface")

def render_chat_interface():
    """Render the main chat interface using Streamlit components."""
    try:
        # Warn if API key missing
        if not st.session_state.get("api_key_set", False):
            st.warning("⚠️ OpenAI API key not set. Please add your API key in the sidebar.")

        st.subheader("Nav Assist")

        # Initialize analysis state
        st.session_state.setdefault("website_analyzed", False)
        st.session_state.setdefault("website_url", None)
        st.session_state.setdefault("site_data", None)

        # Step 1: URL Input
        if not st.session_state.website_analyzed:
            url = render_url_input()
            if url:
                with st.spinner("Analyzing website..."):
                    try:
                        max_depth = st.session_state.get("max_depth", 3)
                        site_data = generate_sitemap(url=url, max_depth=max_depth)
                        st.session_state.site_data = site_data
                        st.session_state.website_url = url
                        st.session_state.website_analyzed = True

                        # Build welcome message
                        msg = generate_website_analyzed_message(site_data)
                        st.session_state.messages = [{"role": "assistant", "content": msg}]

                        # Update conversation metadata if present
                        if (
                            "current_conversation_id" in st.session_state
                            and "conversations" in st.session_state
                        ):
                            cid = st.session_state.current_conversation_id
                            conv = st.session_state.conversations[cid]
                            conv["messages"] = st.session_state.messages
                            conv["title"] = f"Analysis of {site_data['title']}"
                            conv["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            conv["url"] = url

                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error generating sitemap: {e}")
                        st.error(f"Error analyzing website: {e}")
                        st.code(traceback.format_exc())

            if not st.session_state.website_analyzed:
                st.info("Enter a website URL above to get started.")
                return

        # Display analyzed site
        if st.session_state.website_analyzed and st.session_state.site_data:
            with st.expander("Website Structure"):
                display_sitemap(st.session_state.site_data)

            if st.button("Analyze a Different Website"):
                for k in ("website_analyzed", "website_url", "site_data", "agent_result"):
                    st.session_state.pop(k, None)
                new_id = f"conversation_{time.strftime('%Y%m%d_%H%M%S')}"
                st.session_state.current_conversation_id = new_id
                st.session_state.conversations[new_id] = {
                    "title": "New Website Analysis",
                    "messages": [
                        {"role": "assistant", "content": "I'm ready to analyze a new website. Please enter a URL to get started."}
                    ],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.messages = st.session_state.conversations[new_id]["messages"]
                st.rerun()

        # Show chat history
        st.subheader("Conversation")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if st.session_state.website_analyzed:
            placeholder = (
                f"Ask about {st.session_state.site_data['title']}..."
                if st.session_state.site_data and "title" in st.session_state.site_data
                else "Ask about this website..."
            )
            if user_input := st.chat_input(placeholder):
                # Record user message
                st.session_state.messages.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)

                # Let the AI handle everything: display mapping and security
                with st.expander("Query Mapping Analysis"):
                    display_query_mapping(user_input, st.session_state.site_data)

                # Process input with agent
                with st.spinner("Working on your request..."):
                    _process_agent_input(user_input)

                st.rerun()

    except Exception as e:
        logger.error(f"Critical error in chat interface: {e}")
        logger.error(traceback.format_exc())
        st.error(f"Critical error in chat interface: {e}")
        st.code(traceback.format_exc())
        if st.button("Reset Application"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

def _process_agent_input(user_input: str):
    """Process user input with the web agent, using only AI-driven security and relevance."""
    try:
        with st.chat_message("assistant"):
            thinking = st.empty()
            thinking.markdown(
                "🤔 I'm processing your request...\n\n"
                "This may take a moment while I navigate the web."
            )

            # Ensure site_data
            if not st.session_state.get("site_data"):
                thinking.empty()
                err = (
                    "❌ Unable to process your request: website data missing.\n\n"
                    "Please analyze a website first."
                )
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
                return

            # Generate system prompt
            system_prompt = generate_system_prompt(st.session_state.site_data)

            # AI-driven page relevance (no manual checks or fallbacks)
            try:
                relevant_pages = _find_relevant_pages_with_ai(
                    user_input, st.session_state.site_data
                )
                logger.info(f"Found {len(relevant_pages)} pages via SecureMatchAI")
            except SecurityBreachException as sb:
                thinking.empty()
                logger.warning(f"Security breach: {sb}")
                msg = (
                    "⚠️ **Security Alert**: Your query was blocked for security reasons.\n\n"
                    "Please revise your query to legitimate website information."
                )
                st.error(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
                return
            except Exception as e:
                thinking.empty()
                logger.error(f"Relevance scoring failed: {e}")
                err = f"❌ Could not determine relevant pages: {e}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
                return

            # Choose starting URL
            starting_url = None
            if relevant_pages:
                top = relevant_pages[0]
                url = top["url"]
                if not url.startswith("#"):
                    starting_url = (
                        url
                        if url.startswith(("http://", "https://"))
                        else urllib.parse.urljoin(st.session_state.website_url, url)
                    )
                thinking.markdown(f"🤔 Starting from most relevant page: {starting_url or st.session_state.website_url}")

            # Run the agent
            result = asyncio.run(
                run_agent_task(
                    task=user_input,
                    system_prompt=system_prompt,
                    base_url=st.session_state.website_url,
                    starting_url=starting_url,
                    api_key=st.session_state.api_key,
                    headless=st.session_state.get("headless", True),
                    browser_width=st.session_state.get("browser_width", 1280),
                    browser_height=st.session_state.get("browser_height", 800),
                )
            )

            thinking.empty()

            # Display final result (strip any system markers)
            if not isinstance(result, str):
                result = str(result)
            for marker in ["You are SecureWebNavigator", "SECURITY_BREACH_DETECTED"]:
                result = "\n\n".join(p for p in result.split("\n\n") if marker not in p)

            full = f"✅ **Results for:** \"{user_input}\""
            if starting_url:
                full += f"\n\n*Started from:* {starting_url}"
            full += "\n\n" + result

            st.markdown(full)
            st.session_state.messages.append({"role": "assistant", "content": full})

    except Exception as e:
        logger.error(f"Unexpected error in agent: {e}")
        logger.error(traceback.format_exc())
        err = f"❌ An unexpected error occurred: {e}"
        st.error(err)
        st.session_state.messages.append({"role": "assistant", "content": err})
