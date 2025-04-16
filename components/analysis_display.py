import streamlit as st

def display_website_analysis(site_data):
    """Display website analysis results in a structured format."""
    if not site_data:
        return
    
    st.write(f"**Title:** {site_data['title']}")
    
    # Display metadata if available
    if site_data.get('meta_info'):
        with st.expander("Meta Information", expanded=False):
            for key, value in site_data['meta_info'].items():
                st.write(f"**{key}:** {value}")
    
    # Navigation Links
    st.write("**Navigation Links**")
    if site_data.get('navigation_links'):
        # Remove duplicate links by using a dictionary with URL as key
        unique_links = {}
        for link in site_data['navigation_links']:
            url = link['url']
            # Only add if URL not already in unique_links
            if url not in unique_links:
                unique_links[url] = link
        
        # Convert back to list for display
        links_df = [{"Text": link['text'], "URL": link['url'], "Section": link.get('section', 'Main Navigation')} 
                    for link in unique_links.values()]
        
        st.dataframe(links_df, use_container_width=True)
    else:
        st.info("No navigation links found")
    
    # Content Sections
    st.write("**Content Sections**")
    if site_data.get('content_sections'):
        # Create tabs for content sections instead of nested expanders
        section_tabs = st.tabs([
            section.get('heading', f"Section {i+1}") 
            for i, section in enumerate(site_data['content_sections'][:5])
        ])
        
        for i, tab in enumerate(section_tabs):
            section = site_data['content_sections'][i]
            with tab:
                st.write(f"**Length:** {section['length']} characters")
                st.write(section['content'])
    else:
        st.info("No content sections found")

def display_content_search_results(content_info):
    """Display content search results in a structured format."""
    if not content_info:
        return
    
    if 'error' in content_info:
        st.error(f"Error finding information: {content_info['error']}")
        return
    
    if 'content_analysis' not in content_info:
        st.error("Unable to analyze content")
        return
    
    analysis = content_info['content_analysis']
    topic = content_info.get('topic', 'this topic')
    
    st.subheader("Search Results")
    
    if analysis.get('found_content', False) and analysis.get('verified', False):
        st.success(f"Found information about '{topic}' on {content_info.get('url')}")
        
        st.write("**Content Summary**")
        st.write(analysis.get('content_summary', 'No summary available'))
        
        if analysis.get('relevant_content'):
            st.write("**Relevant Content**")
            # Create tabs for the content excerpts
            excerpt_tabs = st.tabs([f"Excerpt {i+1}" for i in range(min(3, len(analysis['relevant_content'])))])
            
            for i, tab in enumerate(excerpt_tabs):
                with tab:
                    st.write(analysis['relevant_content'][i])
        
        if 'source_page' in analysis:
            st.info(f"The content was found on: {analysis['source_page']}")
            
    elif analysis.get('found_content', False) and not analysis.get('verified', False):
        st.warning(
            f"Possibly found information about '{topic}', but verification failed: "
            f"{analysis.get('verification_message', 'unknown reason')}"
        )
        st.write(analysis.get('content_summary', 'No summary available'))
        
    else:
        st.info(f"No direct information about '{topic}' found on the main page")
        
        verified_pages = []
        if 'verified_recommended_pages' in analysis:
            verified_pages = [page for page in analysis.get('verified_recommended_pages', []) 
                             if page.get('verified', False)]
        
        if verified_pages:
            st.success(f"Found {len(verified_pages)} other pages that likely contain information about '{topic}'")
            for i, page in enumerate(verified_pages):
                st.write(f"{i+1}. [{page['url']}]({page['url']})")
            
        elif analysis.get('recommended_pages'):
            st.info("The AI suggests these pages might contain relevant information:")
            for i, page in enumerate(analysis['recommended_pages'][:3]):
                st.write(f"{i+1}. {page}")

def format_navigation_result(success, result, topic):
    """Format the navigation result for display in chat."""
    if success:
        if isinstance(result, dict):
            content = f"✅ Successfully navigated to content about '{topic}'!\n\n"
            
            if 'summary' in result:
                content += f"**Summary:**\n{result['summary']}\n\n"
            
            if 'relevant_excerpts' in result and result['relevant_excerpts']:
                content += "**Relevant excerpts:**\n"
                for i, excerpt in enumerate(result['relevant_excerpts'][:2]):
                    content += f"- {excerpt[:200]}...\n\n"
            
            if 'key_facts' in result and result['key_facts']:
                content += "**Key facts:**\n"
                for fact in result['key_facts'][:3]:
                    content += f"- {fact}\n"
                    
            if 'url' in result:
                content += f"\n**URL:** {result['url']}"
                
            if 'section' in result:
                content += f"\n**Section:** {result['section']}"
                
            return content
        else:
            return f"✅ Successfully navigated to content about '{topic}'. {result}"
    else:
        return f"❌ Failed to navigate to content about '{topic}': {result}"