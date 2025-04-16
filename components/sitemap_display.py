import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from urllib.parse import urlparse

def display_sitemap(site_data: Dict[str, Any]):
    """
    Display a sitemap visualization based on site structure data.
    
    Args:
        site_data: Dictionary containing site structure information
    """
    if not site_data:
        st.error("No site data available to display.")
        return
    
    # Display site title and basic info
    st.write(f"## {site_data['title']}")
    st.write(f"**URL:** {site_data['url']}")
    
    # Create tabs for different sitemap views
    tabs = st.tabs(["Overview", "Navigation", "Content", "Links", "Forms", "Social"])
    
    # Overview Tab
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Internal Links", site_data.get('internal_link_count', 0))
        with col2:
            st.metric("External Links", site_data.get('external_link_count', 0))
        with col3:
            content_length = sum([section.get('length', 0) for section in site_data.get('content_sections', [])])
            st.metric("Content Size", f"{content_length:,} chars")
        
        # Site metadata
        if site_data.get('meta_info'):
            st.subheader("Metadata")
            meta_table = []
            for key, value in site_data['meta_info'].items():
                meta_table.append({"Property": key, "Content": value})
            
            if meta_table:
                st.table(meta_table)
        
        # Display mapping status if available
        domain = urlparse(site_data['url']).netloc
        if hasattr(site_data, 'mapping_status') and domain in site_data.get('mapping_status', {}):
            status = site_data['mapping_status'][domain]
            st.info(f"Mapping status: {status}")
    
    # Navigation Tab
    with tabs[1]:
        if site_data.get('navigation_links'):
            st.subheader("Navigation Structure")
            
            # Group by section
            nav_sections = {}
            for link in site_data['navigation_links']:
                section = link.get('section', 'Main Navigation')
                if section not in nav_sections:
                    nav_sections[section] = []
                nav_sections[section].append(link)
            
            # Display each section
            for section, links in nav_sections.items():
                st.write(f"**{section}** ({len(links)} links)")
                
                # Create dataframe for better display
                links_df = pd.DataFrame([
                    {"Text": link['text'], 
                     "URL": link['url'], 
                     "External": link.get('is_external', False)} 
                    for link in links
                ])
                
                st.dataframe(links_df, use_container_width=True, hide_index=True)
        else:
            st.info("No navigation links found on this site.")
    
    # Content Structure Tab
    with tabs[2]:
        if site_data.get('content_sections'):
            st.subheader("Content Sections")
            
            # Use a selectbox instead of expanders to avoid nesting issues
            section_titles = [
                section.get('heading', f"Section {i+1}") + f" ({section.get('length', 0)} chars)"
                for i, section in enumerate(site_data['content_sections'])
            ]
            
            if section_titles:
                selected_section = st.selectbox("Select a content section to view:", section_titles)
                
                # Display the selected section
                if selected_section:
                    # Get the index of the selected section
                    selected_index = section_titles.index(selected_section)
                    st.markdown("### " + section_titles[selected_index])
                    st.write(site_data['content_sections'][selected_index].get('content', 'No content available'))
        else:
            st.info("No content sections were identified.")
    
    # Link Analysis Tab
    with tabs[3]:
        st.subheader("Site Structure Analysis")
        
        # Site structure visualization
        if site_data.get('sitemap_structure') and 'linksByDepth' in site_data['sitemap_structure']:
            # Extract sitemap data
            hostname = site_data['sitemap_structure'].get('hostname', '')
            links_by_depth = site_data['sitemap_structure'].get('linksByDepth', {})
            
            # Display visualization
            st.write("**URL Structure by Depth**")
            
            # Create bar chart of links by depth
            depth_counts = {int(depth): len(links) for depth, links in links_by_depth.items() if links}
            
            if depth_counts:
                depths = sorted(depth_counts.keys())
                counts = [depth_counts[d] for d in depths]
                
                # Create a readable labels
                labels = [f"Depth {d}" for d in depths]
                
                # Create dataframe for chart
                chart_data = pd.DataFrame({
                    "Depth": labels,
                    "URL Count": counts
                })
                
                st.bar_chart(chart_data, x="Depth", y="URL Count")
                
                # Use a selectbox for depth selection instead of nested expanders
                depth_options = [f"Depth {depth} ({len(links_by_depth.get(str(depth), []))} URLs)" 
                                for depth in sorted([int(d) for d in links_by_depth.keys()]) if links_by_depth.get(str(depth))]
                
                if depth_options:
                    selected_depth = st.selectbox("Select a depth level to view URLs:", depth_options)
                    
                    if selected_depth:
                        # Extract the depth number from the selected option
                        depth_num = int(selected_depth.split()[1].split('(')[0])
                        depth_links = links_by_depth.get(str(depth_num), [])
                        
                        if depth_links:
                            # Create a simplified view of the first 20 links
                            links_sample = depth_links[:20]
                            
                            # Create dataframe
                            df = pd.DataFrame([
                                {"Path": link.get('path', ''), "Full URL": link.get('url', '')} 
                                for link in links_sample
                            ])
                            
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            
                            if len(depth_links) > 20:
                                st.info(f"Showing 20 of {len(depth_links)} URLs at this depth")
            else:
                st.info("No structure information available")
        else:
            st.info("No site structure information available")
        
        # Link distribution: internal vs external
        st.subheader("Internal vs External Links")
        
        # Create pie chart data
        link_data = pd.DataFrame([
            {"Category": "Internal Links", "Count": site_data.get('internal_link_count', 0)},
            {"Category": "External Links", "Count": site_data.get('external_link_count', 0)}
        ])
        
        # Only show if we have links
        if site_data.get('internal_link_count', 0) + site_data.get('external_link_count', 0) > 0:
            st.line_chart(link_data, x="Category", y="Count")
    
    # Forms Tab (New)
    with tabs[4]:
        if site_data.get('forms'):
            st.subheader("Forms Detected")
            
            # Create a selectbox for forms instead of expanders
            form_titles = [
                f"{form.get('purpose', 'Unknown').capitalize()} Form ({form.get('method', 'GET')})"
                for form in site_data['forms']
            ]
            
            if form_titles:
                selected_form = st.selectbox("Select a form to view details:", form_titles)
                
                if selected_form:
                    # Get the index of the selected form
                    selected_index = form_titles.index(selected_form)
                    form = site_data['forms'][selected_index]
                    
                    # Display form details
                    form_action = form.get('action', '')
                    st.write(f"**Action:** {form_action}")
                    
                    # Display form fields
                    if form.get('fields'):
                        st.write("**Fields:**")
                        fields_df = pd.DataFrame([
                            {"Field": field.get('name', 'unnamed'),
                             "Type": field.get('type', 'text'),
                             "Required": field.get('required', False),
                             "Placeholder": field.get('placeholder', '')}
                            for field in form['fields']
                        ])
                        st.dataframe(fields_df, use_container_width=True, hide_index=True)
        else:
            st.info("No forms detected on this website.")
    
    # Social Media Tab (New)
    with tabs[5]:
        if site_data.get('social_links'):
            st.subheader("Social Media Profiles")
            
            # Group by platform
            platforms = {}
            for link in site_data['social_links']:
                platform = link.get('platform', 'other')
                if platform not in platforms:
                    platforms[platform] = []
                platforms[platform].append(link)
            
            # Display each platform
            for platform, links in platforms.items():
                st.write(f"**{platform.capitalize()}**")
                
                # Show links
                for link in links:
                    st.write(f"[{link.get('text', link.get('url'))}]({link.get('url')})")
        else:
            st.info("No social media links detected on this website.")