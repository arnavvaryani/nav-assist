import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse
import re

def display_query_mapping(user_query: str, site_data: Dict[str, Any], top_n: int = 3):
    """
    Display a visual representation of how the user query is mapped to relevant pages in the sitemap.
    
    Args:
        user_query: The user's query
        site_data: Dictionary containing site structure information
        top_n: Number of top matches to display
    """
    if not site_data or not user_query:
        return
    
    st.write("### Query Mapping Analysis")
    st.write(f"Query: \"{user_query}\"")
    
    # Extract keywords from the query
    query_keywords = _extract_keywords(user_query)
    
    # Display the identified topics
    if query_keywords:
        st.write("**Identified Topics:**")
        st.write(", ".join(query_keywords))
    
    # Find relevant pages based on query
    relevant_pages = _find_relevant_pages(user_query, query_keywords, site_data)
    
    # Display the matched pages in a table
    if relevant_pages:
        st.write("**Potentially Relevant Pages:**")
        
        # Create dataframe for display
        df = pd.DataFrame(
            [{"Page": p["title"], 
              "URL": p["url"], 
              "Relevance Score": p["score"], 
              "Matched Topics": ", ".join(p["matched_topics"])} 
             for p in relevant_pages[:top_n]]
        )
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Highlight the most relevant page
        if relevant_pages:
            best_match = relevant_pages[0]
            st.success(f"**Best Match:** {best_match['title']} ({best_match['url']})")
    else:
        st.warning("No specific pages could be matched to the query. Starting from the homepage.")

def _extract_keywords(text: str) -> List[str]:
    """Extract keywords from text."""
    # Simple keyword extraction
    words = re.findall(r'\b[a-zA-Z]{3,15}\b', text.lower())
    
    # Remove common stop words
    stop_words = {
        'the', 'and', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'from', 'about', 'as', 'into', 'like', 'through', 'after', 'over', 'between',
        'out', 'against', 'during', 'before', 'because', 'that', 'then', 'than', 'this',
        'these', 'those', 'there', 'here', 'when', 'where', 'which', 'who', 'what',
        'how', 'why', 'page', 'website', 'site', 'click', 'view', 'read', 'more', 'find',
        'information', 'look'
    }
    
    # Return unique keywords, excluding stop words
    return list(set([word for word in words if word not in stop_words]))

def _find_relevant_pages(query: str, keywords: List[str], site_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Find pages in the sitemap that are relevant to the user's query.
    
    Args:
        query: The user's query
        keywords: Extracted keywords from the query
        site_data: Website structure data
    
    Returns:
        List of relevant pages with scores
    """
    relevant_pages = []
    
    # Check navigation links
    if site_data.get('navigation_links'):
        for link in site_data['navigation_links']:
            score, matched_topics = _calculate_page_relevance(link, keywords, query)
            if score > 0:
                relevant_pages.append({
                    "title": link.get('text', 'Navigation Link'),
                    "url": link.get('url', ''),
                    "section": link.get('section', 'Main Navigation'),
                    "score": score,
                    "matched_topics": matched_topics
                })
    
    # Check specific topic mapping patterns
    topic_mappings = {
        r'\b(?:contact|reach|email|phone|call)\b': ['contact', 'about us', 'get in touch'],
        r'\b(?:price|cost|plan|subscription|buy|purchase)\b': ['pricing', 'plans', 'shop', 'store'],
        r'\b(?:about|who|company|team|staff|people)\b': ['about', 'company', 'team', 'our story'],
        r'\b(?:help|support|faq|question|problem)\b': ['help', 'support', 'faq', 'knowledge base'],
        r'\b(?:login|signin|log in|sign in|account)\b': ['login', 'sign in', 'account', 'my account'],
        r'\b(?:product|service|offer|solution)\b': ['products', 'services', 'solutions', 'what we do'],
    }
    
    # Check for specific topic matches
    for pattern, topics in topic_mappings.items():
        if re.search(pattern, query.lower()):
            # Boost pages that match these topics
            for link in site_data.get('navigation_links', []):
                link_text = link.get('text', '').lower()
                link_url = link.get('url', '').lower()
                
                # Check if any topic matches in the link text or URL
                for topic in topics:
                    if topic in link_text or topic in link_url:
                        # This is a strong topical match, boost the score
                        score = 10  # High base score for direct topic match
                        matched_keywords = [topic]
                        
                        # Add to relevant pages with high score
                        relevant_pages.append({
                            "title": link.get('text', 'Navigation Link'),
                            "url": link.get('url', ''),
                            "section": link.get('section', 'Main Navigation'),
                            "score": score,
                            "matched_topics": matched_keywords
                        })
    
    # Check content sections if available
    if site_data.get('content_sections'):
        for i, section in enumerate(site_data['content_sections']):
            heading = section.get('heading', f"Section {i+1}")
            content = section.get('content', '')
            
            # Create a mock link object for scoring
            section_link = {
                'text': heading,
                'url': f"#{heading.lower().replace(' ', '-')}",  # Mock URL as anchor
                'section': 'Content Section',
                'content': content[:200]  # Use a snippet of content
            }
            
            score, matched_topics = _calculate_page_relevance(section_link, keywords, query)
            if score > 0:
                relevant_pages.append({
                    "title": heading,
                    "url": section_link['url'],
                    "section": 'Content Section',
                    "score": score,
                    "matched_topics": matched_topics
                })
    
    # Sort by relevance score
    relevant_pages.sort(key=lambda x: x['score'], reverse=True)
    
    return relevant_pages

def _calculate_page_relevance(link: Dict[str, Any], keywords: List[str], query: str) -> Tuple[float, List[str]]:
    """
    Calculate how relevant a page is to the query.
    
    Args:
        link: Dictionary with link information
        keywords: Keywords extracted from the query
        query: The original query
    
    Returns:
        Tuple of (relevance_score, matched_keywords)
    """
    score = 0
    matched_keywords = []
    
    # Get link text and URL
    link_text = link.get('text', '').lower()
    link_url = link.get('url', '').lower()
    link_section = link.get('section', '').lower()
    
    # Direct match bonus - if the entire query appears in the link text
    if query.lower() in link_text:
        score += 5
        matched_keywords.append(query.lower())
    
    # Check each keyword
    for keyword in keywords:
        # Check if keyword is in link text (highest weight)
        if keyword in link_text:
            score += 2
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)
        
        # Check if keyword is in URL path (medium weight)
        path = urlparse(link_url).path.lower()
        if keyword in path:
            score += 1
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)
                
        # Check if keyword is in section name (medium weight)
        if keyword in link_section:
            score += 1
            if keyword not in matched_keywords:
                matched_keywords.append(keyword)
        
        # If link has content snippet, check that too
        if 'content' in link and link['content']:
            content = link['content'].lower()
            if keyword in content:
                score += 0.5
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)
    
    # Bonus for navigation sections that are typically important
    important_sections = ['main navigation', 'header navigation', 'primary navigation']
    if link_section in important_sections:
        score += 0.5
    
    return score, matched_keywords