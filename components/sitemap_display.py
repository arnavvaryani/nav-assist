import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from urllib.parse import urlparse

def show_table(data: List[dict], **kwargs) -> None:
    """
    Render a pandas DataFrame in Streamlit from a list of dicts.
    """
    if not data:
        st.info("No data to display.")
        return
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)

def render_overview(site_data: Dict[str, Any]) -> None:
    """
    Overview tab: metrics, metadata, and mapping status.
    """
    col1, col2, col3 = st.columns(3)
    internal = site_data.get('internal_link_count', 0)
    external = site_data.get('external_link_count', 0)
    content_sections = site_data.get('content_sections', [])
    content_length = sum(sec.get('length', 0) for sec in content_sections)

    col1.metric("Internal Links", internal)
    col2.metric("External Links", external)
    col3.metric("Content Size", f"{content_length:,} chars")

    meta_info = site_data.get('meta_info', {})
    if meta_info:
        st.subheader("Metadata")
        table = [{"Property": k, "Content": v} for k, v in meta_info.items()]
        show_table(table)

    mapping = site_data.get('mapping_status', {})
    domain = urlparse(site_data.get('url', "")).netloc
    if domain in mapping:
        st.info(f"Mapping status for {domain}: {mapping[domain]}")

def render_navigation(site_data: Dict[str, Any]) -> None:
    """
    Navigation tab: grouped navigation links.
    """
    nav_links = site_data.get('navigation_links', [])
    if not nav_links:
        st.info("No navigation links found on this site.")
        return

    st.subheader("Navigation Structure")
    sections: Dict[str, List[dict]] = {}
    for link in nav_links:
        sec = link.get('section', 'Main Navigation')
        sections.setdefault(sec, []).append(link)

    for section, links in sections.items():
        st.write(f"**{section}** ({len(links)} links)")
        table = [
            {"Text": l.get('text', ''), "URL": l.get('url', ''), "External": l.get('is_external', False)}
            for l in links
        ]
        show_table(table)

def render_content(site_data: Dict[str, Any]) -> None:
    """
    Content tab: select and display individual content sections.
    """
    sections = site_data.get('content_sections', [])
    if not sections:
        st.info("No content sections were identified.")
        return

    st.subheader("Content Sections")
    titles = [
        f"{sec.get('heading', f'Section {i+1}')} ({sec.get('length', 0)} chars)"
        for i, sec in enumerate(sections)
    ]
    choice = st.selectbox("Select a section to view:", titles)
    idx = titles.index(choice)
    st.markdown(f"### {titles[idx]}")
    st.write(sections[idx].get('content', 'No content available'))

def render_link_analysis(site_data: Dict[str, Any]) -> None:
    """
    Links tab: sitemap depth chart and internal vs. external distribution.
    """
    st.subheader("Site Structure Analysis")
    sitemap = site_data.get('sitemap_structure', {})
    links_by_depth = sitemap.get('linksByDepth', {})

    if links_by_depth:
        # bar chart of counts by depth
        depth_counts = {int(d): len(v) for d, v in links_by_depth.items()}
        df = pd.DataFrame({
            "Depth": [f"Depth {d}" for d in sorted(depth_counts)],
            "URL Count": [depth_counts[d] for d in sorted(depth_counts)]
        })
        st.bar_chart(df.set_index("Depth"))

        # show URLs at selected depth
        options = [
            f"Depth {d} ({depth_counts[d]} URLs)"
            for d in sorted(depth_counts)
        ]
        sel = st.selectbox("Select depth level to view URLs:", options)
        depth_num = int(sel.split()[1])
        urls = links_by_depth.get(str(depth_num), [])
        sample = urls[:20]
        table = [{"Path": u.get('path', ''), "Full URL": u.get('url', '')} for u in sample]
        show_table(table)
        if len(urls) > 20:
            st.info(f"Showing 20 of {len(urls)} URLs at this depth")
    else:
        st.info("No sitemap structure information available")

    st.subheader("Internal vs External Links")
    total = site_data.get('internal_link_count', 0) + site_data.get('external_link_count', 0)
    if total:
        df2 = pd.DataFrame([
            {"Category": "Internal Links", "Count": site_data.get('internal_link_count', 0)},
            {"Category": "External Links", "Count": site_data.get('external_link_count', 0)}
        ]).set_index("Category")
        st.bar_chart(df2)
    else:
        st.info("No links to display in distribution chart")

def render_forms(site_data: Dict[str, Any]) -> None:
    """
    Forms tab: list detected forms and their fields.
    """
    forms = site_data.get('forms', [])
    if not forms:
        st.info("No forms detected on this website.")
        return

    st.subheader("Forms Detected")
    titles = [
        f"{f.get('purpose','Unknown').capitalize()} Form ({f.get('method','GET')})"
        for f in forms
    ]
    sel = st.selectbox("Select a form to view details:", titles)
    idx = titles.index(sel)
    form = forms[idx]

    st.write(f"**Action:** {form.get('action','')}")
    fields = form.get('fields', [])
    if fields:
        table = [
            {
                "Field": fld.get('name',''),
                "Type": fld.get('type','text'),
                "Required": fld.get('required', False),
                "Placeholder": fld.get('placeholder','')
            }
            for fld in fields
        ]
        show_table(table)

def render_social(site_data: Dict[str, Any]) -> None:
    """
    Social tab: grouped social media profile links.
    """
    social_links = site_data.get('social_links', [])
    if not social_links:
        st.info("No social media links detected on this website.")
        return

    st.subheader("Social Media Profiles")
    platforms: Dict[str, List[dict]] = {}
    for link in social_links:
        plat = link.get('platform','other').lower()
        platforms.setdefault(plat, []).append(link)

    for plat, links in platforms.items():
        st.write(f"**{plat.capitalize()}**")
        for l in links:
            text = l.get('text') or l.get('url')
            url = l.get('url')
            st.markdown(f"[{text}]({url})")

def display_sitemap(site_data: Dict[str, Any]) -> None:
    """
    Display a multi-tab sitemap visualization given site structure data.
    """
    if not site_data:
        st.error("No site data available to display.")
        return

    # Header
    st.write(f"## {site_data.get('title','')}")
    st.write(f"**URL:** {site_data.get('url','')}")

    # Tabs
    tabs = st.tabs(["Overview", "Navigation", "Content", "Links", "Forms", "Social"])
    with tabs[0]:
        render_overview(site_data)
    with tabs[1]:
        render_navigation(site_data)
    with tabs[2]:
        render_content(site_data)
    with tabs[3]:
        render_link_analysis(site_data)
    with tabs[4]:
        render_forms(site_data)
    with tabs[5]:
        render_social(site_data)
