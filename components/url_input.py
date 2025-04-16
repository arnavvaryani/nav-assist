import streamlit as st
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger("url_input")

def is_valid_url(url: str) -> bool:
    """
    Validate if the provided string is a valid URL.
    
    Args:
        url: String to validate as URL
        
    Returns:
        True if valid URL, False otherwise
    """
    # Basic validation
    if not url or len(url) < 4:  # http: is 5 chars minimum
        return False
    
    # Check if it has a scheme
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    
    # More thorough regex validation
    regex = re.compile(
        r'^(?:http|https)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ipv4
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return re.match(regex, url) is not None

def render_url_input():
    """
    Render the URL input component with validation.
    
    Returns:
        The validated URL if submitted, None otherwise
    """
    st.subheader("🔍 Website URL Analysis")
    
    with st.form(key="url_form"):
        # URL input field with validation
        url = st.text_input(
            "Enter the website URL you want to analyze",
            placeholder="https://example.com",
            help="Enter a complete URL including the http:// or https:// prefix"
        )
        
        # Form submission button
        submit_button = st.form_submit_button("Analyze Website")
        
        if submit_button:
            # Validate URL format
            if not url:
                st.error("Please enter a URL.")
                return None
                
            # Ensure URL has http/https prefix
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                st.info(f"Added https:// prefix: {url}")
            
            # Final validation
            if not is_valid_url(url):
                st.error("Please enter a valid URL (e.g., https://example.com).")
                return None
                
            logger.info(f"URL submitted for analysis: {url}")
            return url
            
    return None