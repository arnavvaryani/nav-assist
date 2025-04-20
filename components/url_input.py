import streamlit as st
import logging
import re
from urllib.parse import urlparse, urlunparse
from typing import Optional

logger = logging.getLogger("url_input")
logger.setLevel(logging.INFO)

# ——— Pre‑compile the regex once ——————————————————————————————————
_URL_REGEX = re.compile(
    r'^(?:http|https)://'                              # scheme
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'   # domain...
    r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'              # …including TLD
    r'localhost|'                                       # localhost
    r'\d{1,3}(?:\.\d{1,3}){3})'                         # or IPv4
    r'(?::\d+)?'                                        # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

def normalize_url(raw: str) -> str:
    """
    Trim whitespace and ensure URL has an http(s) scheme.
    """
    raw = raw.strip()
    if not raw.lower().startswith(("http://", "https://")):
        raw = "https://" + raw
    # Re‑parse and re‑rebuild to normalize things like trailing slashes
    parts = urlparse(raw)
    return urlunparse(parts._replace(path=parts.path or "/"))

def is_valid_url(url: str) -> bool:
    """
    Return True if `url` is a well‑formed HTTP/HTTPS URL.
    """
    try:
        parts = urlparse(url)
    except Exception:
        return False

    if parts.scheme not in ("http", "https") or not parts.netloc:
        return False

    return bool(_URL_REGEX.match(url))

def render_url_input() -> Optional[str]:
    """
    Render a Streamlit form for URL entry & validation.
    Returns the normalized URL on success, or None.
    """
    st.subheader("🔍 Website URL Analysis")

    # Preserve what the user typed across reruns
    if "raw_url" not in st.session_state:
        st.session_state.raw_url = ""

    with st.form("url_form"):
        url_in = st.text_input(
            "Enter the website URL you want to analyze",
            value=st.session_state.raw_url,
            placeholder="https://example.com",
            help="Include http:// or https://"
        )
        submit = st.form_submit_button("Analyze Website")

        if submit:
            st.session_state.raw_url = url_in  # remember it

            if not url_in:
                st.error("Please enter a URL.")
                return None

            normalized = normalize_url(url_in)
            if normalized != url_in.strip():
                st.info(f"Using normalized URL: {normalized}")

            if not is_valid_url(normalized):
                st.error("Invalid URL. Examples: https://example.com or http://localhost:8000")
                logger.warning(f"URL validation failed: {normalized}")
                return None

            logger.info(f"URL submitted for analysis: {normalized}")
            return normalized

    return None
