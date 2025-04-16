import logging
from typing import Dict, Any, List
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger("prompts")

def generate_system_prompt(site_data: Dict[str, Any]) -> str:
    """
    Generate a system prompt for the agent based on site structure.
    
    Args:
        site_data: The site structure data
        
    Returns:
        A system prompt string for the agent
    """
    if not site_data or "error" in site_data:
        return "You are a web assistant trying to help the user navigate a website that couldn't be analyzed properly. Try your best to understand the site structure as you navigate."
    
    # Build the system prompt with site information
    prompt = f"""You are a specialized web assistant analyzing {site_data['url']}. 
    
Site title: {site_data['title']}
Internal links: {site_data['internal_link_count']}
External links: {site_data['external_link_count']}

Your task is to help the user find specific information on this webpage. Here's what you know about the site structure:

1. The site has {len(site_data.get('navigation_links', []))} navigation links in its main menu.
"""

    # Add navigation structure if available
    if site_data.get('navigation_links'):
        prompt += "\nMain navigation sections:\n"
        nav_sections = {}
        
        for link in site_data['navigation_links']:
            section = link.get('section', 'Main Navigation')
            if section not in nav_sections:
                nav_sections[section] = []
            nav_sections[section].append(f"- {link['text']} ({link['url']})")
        
        for section, links in nav_sections.items():
            prompt += f"\n{section}:\n" + "\n".join(links[:5])
            if len(links) > 5:
                prompt += f"\n...and {len(links) - 5} more links"
    
    # Add content structure if available
    if site_data.get('content_sections'):
        prompt += "\n\nMain content sections:\n"
        for i, section in enumerate(site_data['content_sections'][:3]):
            heading = section.get('heading', f"Section {i+1}")
            prompt += f"- {heading} ({section['length']} characters)\n"
        
        if len(site_data['content_sections']) > 3:
            prompt += f"...and {len(site_data['content_sections']) - 3} more content sections"
    
    # Add sitemap depth information
    if site_data.get('sitemap_structure') and 'linksByDepth' in site_data['sitemap_structure']:
        prompt += "\n\nSite structure by depth:\n"
        
        for depth, links in site_data['sitemap_structure']['linksByDepth'].items():
            prompt += f"- Depth {depth}: {len(links)} unique URLs\n"
    
    # Add forms information if available
    if site_data.get('forms'):
        prompt += "\n\nThe site contains the following forms:\n"
        for i, form in enumerate(site_data['forms'][:3]):
            purpose = form.get('purpose', 'unknown')
            prompt += f"- {purpose.capitalize()} form with {len(form.get('fields', []))} fields\n"
    
    # Add social media links if available
    if site_data.get('social_links'):
        prompt += "\n\nSocial media presence:\n"
        platforms = list(set(link.get('platform') for link in site_data['social_links']))
        prompt += "- " + ", ".join(platform.capitalize() for platform in platforms[:5])
    
    # Add instructions for the agent
    prompt += """

When navigating this site:
1. Use the navigation structure to find relevant sections first
3. Scan content sections for relevant information
4. Be aware of the site's depth structure when looking for specific pages

Your goal is to efficiently find the information the user requests by using your knowledge of this site's structure.
"""
    
    return prompt

def generate_task_prompt(user_query: str, site_data: Dict[str, Any]) -> str:
    """
    Generate a task prompt for the agent based on the user query and site structure.
    
    Args:
        user_query: The user's query
        site_data: The site structure data
        
    Returns:
        A task prompt string for the agent
    """
    base_url = site_data.get('url', '')
    
    # Detect specific types of queries and use specialized prompts
    # Default general-purpose prompt
    
    prompt = f"""
TASK: {user_query}

You should navigate the website at {base_url} to find information that answers this query.
Follow these steps:

1. First, analyze the query to understand what information the user is looking for
2. Based on the site structure you know, identify the most likely page(s) where this information would be found
3. Navigate to those pages and extract the relevant information
4. If you can't find the information in the expected pages, try to use site search or related navigation links
5. Provide a detailed answer based on the information you find

Remember to always cite the specific pages where you found the information.
"""

    return prompt


def generate_conversation_intro() -> str:
    """
    Generate the initial conversation message.
    
    Returns:
        A string with the welcome message
    """
    return "Hello! I'm your Website Analyzer. I can help you analyze any website and find information for you. Please enter a website URL to get started."

def generate_website_analyzed_message(site_data: Dict[str, Any]) -> str:
    """
    Generate a welcome message after a website has been successfully analyzed.
    
    Args:
        site_data: The site structure data
        
    Returns:
        A welcome message string with site information
    """
    url = site_data.get('url', 'the website')
    
    # Create welcome message with site info
    welcome_message = f"✅ Successfully analyzed website: {site_data['title']} ({url})\n\n"
    
    # Add information about the sitemap
    welcome_message += f"I've mapped the structure of this website and found {site_data['internal_link_count']} internal links"
    if 'external_link_count' in site_data:
        welcome_message += f" and {site_data['external_link_count']} external links"
    welcome_message += ".\n\n"
    
    # Add information about content sections if available
    if 'content_sections' in site_data and site_data['content_sections']:
        welcome_message += f"I've identified {len(site_data['content_sections'])} main content sections.\n\n"
    
    # Add information about forms if available
    if 'forms' in site_data and site_data['forms']:
        form_types = {form.get('purpose', 'unknown') for form in site_data['forms']}
        welcome_message += f"The site contains {len(site_data['forms'])} forms including: {', '.join(form_types)}.\n\n"
    
    # Add information about social links if available
    if 'social_links' in site_data and site_data['social_links']:
        platforms = {link.get('platform', 'unknown') for link in site_data['social_links']}
        welcome_message += f"I found social media links for: {', '.join(platforms)}.\n\n"
    
    welcome_message += "You can now ask me about any specific information you'd like to find on this website."
    
    return welcome_message