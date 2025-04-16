import logging
import traceback
import time
import json
from typing import Dict, List, Any, Set, Optional
from urllib.parse import urlparse, urljoin
import re
import threading
import queue

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("sitemap_service")

class WebsiteSitemapExtractor:
    """Comprehensive class for extracting sitemap information from websites."""
    
    def __init__(self, requests_per_minute: int = 20, max_pages: int = 30, max_depth: int = 2):
        """
        Initialize the WebsiteSitemapExtractor.
        
        Args:
            requests_per_minute: Maximum number of requests per minute to respect website load
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum depth to crawl from the starting URL
        """
        # Configuration
        self.requests_per_minute = requests_per_minute
        self.request_interval = 60.0 / max(1, requests_per_minute)
        self.max_pages = max_pages
        self.max_depth = max_depth
        
        # State
        self.site_maps = {}  # Store site maps by domain
        self.last_request_time = {}  # For rate limiting
        self.mapping_status = {}  # Track mapping status by domain
        self.content_cache = {}  # Cache for page content
        
        # Stats
        self.stats = {
            "total_pages_mapped": 0,
            "total_errors": 0,
            "start_time": time.time()
        }
        
        # Setup requests session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        })
        
        # Thread lock for rate limiting
        self.rate_limit_lock = threading.Lock()
    
    def extract_sitemap(self, url: str, background_mapping: bool = True) -> Dict[str, Any]:
        """
        Extract sitemap information from a website.
        
        Args:
            url: The URL to extract sitemap from
            background_mapping: Whether to continue mapping in the background
            
        Returns:
            Dictionary containing initial site structure information
        """
        # Normalize URL
        url = self._normalize_url(url)
        domain = urlparse(url).netloc
        
        # Fetch initial page
        html_content = self.fetch_website_content(url)
        if not html_content:
            return {"error": "Failed to fetch website content"}
        
        # Extract site structure
        site_data = self.extract_site_structure(html_content, url)
        
        # Initialize site map for this domain if not exists
        if domain not in self.site_maps:
            self.site_maps[domain] = {}
        
        # Store initial page data in the site map
        self.site_maps[domain][url] = {
            "title": site_data.get("title", ""),
            "links": site_data.get("navigation_links", []),
            "crawled_at": time.time()
        }
        
        # Start background mapping if requested
        if background_mapping:
            self.start_site_mapping(url)
        
        return site_data
    
    def extract_site_structure(self, html_content: str, base_url: str) -> Dict[str, Any]:
        """
        Extract basic structure information from a website's HTML content.
        
        Args:
            html_content: The HTML content of the website
            base_url: The base URL of the website
            
        Returns:
            Dictionary containing site structure information
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract basic site information
            site_data = {
                "title": self._extract_title(soup),
                "navigation_links": [],
                "content_sections": [],
                "forms": [],
                "social_links": [],
                "meta_info": self._extract_meta_info(soup)
            }
            
            # Extract navigation links
            site_data["navigation_links"] = self._extract_navigation_links(soup, base_url)
            
            # Extract additional navigation elements
            additional_links = self._extract_additional_navigation(soup, base_url)
            site_data["navigation_links"].extend(additional_links)
            
            # Extract content sections
            site_data["content_sections"] = self._extract_content_sections(soup)
            
            # Extract forms
            site_data["forms"] = self._extract_forms(soup)
            
            # Extract social links
            site_data["social_links"] = self._extract_social_links(soup, base_url)
            
            return site_data
            
        except Exception as e:
            return {"error": f"Error extracting site structure: {str(e)}"}
    
    def start_site_mapping(self, base_url: str) -> bool:
        """
        Start a background thread to map the site structure by crawling linked pages.
        
        Args:
            base_url: The base URL to start mapping from
            
        Returns:
            True if mapping started, False if already in progress or completed
        """
        domain = urlparse(base_url).netloc
        
        # Don't remap if we already have a mapping in progress
        if domain in self.mapping_status and self.mapping_status[domain] == "in_progress":
            print(f"Site mapping already in progress for {domain}")
            return False
        
        # Update mapping status
        self.mapping_status[domain] = "in_progress"
        
        # Start a background thread for site mapping
        thread = threading.Thread(
            target=self._map_site_structure, 
            args=(base_url,),
            name=f"SiteMapper-{domain}"
        )
        thread.daemon = True  # Make thread exit when main program exits
        thread.start()
        
        print(f"Started site mapping for {domain}")
        return True
    
    def _map_site_structure(self, base_url: str) -> None:
        """
        Map the site structure by following links from the base URL.
        
        Args:
            base_url: The base URL to start mapping from
        """
        domain = urlparse(base_url).netloc
        visited: Set[str] = set()
        to_visit: queue.Queue = queue.Queue()
        to_visit.put((base_url, 0))  # (url, depth)
        error_count = 0
        
        try:
            logger.info(f"Starting site mapping for {domain}")
            
            # Track start time for performance monitoring
            start_time = time.time()
            
            while not to_visit.empty() and len(visited) < self.max_pages and error_count < self.max_pages * 0.5:
                url, depth = to_visit.get()
                
                if url in visited or depth > self.max_depth:
                    continue
                
                # Only process pages on the same domain
                if urlparse(url).netloc != domain:
                    continue
                
                # Apply rate limiting
                self._apply_rate_limiting(domain)
                
                # Mark as visited
                visited.add(url)
                
                try:
                    # Fetch page content
                    html_content = self.fetch_website_content(url)
                    
                    if not html_content:
                        logger.warning(f"No content fetched for {url}")
                        error_count += 1
                        continue
                    
                    # Parse and extract page info
                    try:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Extract page title
                        title = self._extract_title(soup)
                        
                        # Extract page navigation links
                        navigation_links = self._extract_navigation_links(soup, url)
                        
                        # Extract keywords for search relevance
                        text = soup.get_text(" ", strip=True)
                        keywords = self._extract_keywords(text[:5000])  # Limit text size
                        
                        # Extract topic relevance indicators from headings
                        headings = []
                        for h_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            for heading in soup.find_all(h_tag):
                                if heading.text.strip():
                                    headings.append(heading.text.strip())
                        
                        # Store page info in site map
                        self.site_maps[domain][url] = {
                            "title": title,
                            "links": navigation_links,
                            "keywords": list(keywords),
                            "headings": headings[:10],  # Store limited number of headings
                            "crawled_at": time.time()
                        }
                        
                        # Update total pages counter
                        self.stats["total_pages_mapped"] += 1
                        
                        logger.info(f"Mapped page {url} (depth {depth}), {len(visited)}/{self.max_pages} pages")
                        
                        # Add linked pages to the queue for next depth
                        if depth < self.max_depth:
                            # Prioritize: internal content pages first, then navigation links
                            content_links = []
                            nav_links = []
                            
                            for link in navigation_links:
                                link_url = link["url"]
                                
                                # Skip already visited or external links
                                if link_url in visited or urlparse(link_url).netloc != domain:
                                    continue
                                    
                                # Classify the link as content or navigation
                                is_nav = link.get("section", "").lower() in ["main navigation", "header navigation"]
                                if is_nav:
                                    nav_links.append((link_url, depth + 1))
                                else:
                                    content_links.append((link_url, depth + 1))
                            
                            # Add content links first, then navigation links
                            for link_info in content_links:
                                to_visit.put(link_info)
                                
                            for link_info in nav_links:
                                to_visit.put(link_info)
                    
                    except Exception as parse_error:
                        logger.error(f"Error parsing page {url}: {str(parse_error)}")
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error mapping page {url}: {str(e)}")
                    error_count += 1
            
            # Calculate statistics
            elapsed_time = time.time() - start_time
            pages_per_second = len(visited) / max(1, elapsed_time)
            
            # Update mapping status
            self.mapping_status[domain] = "completed"
            logger.info(f"Site mapping completed for {domain}. Mapped {len(visited)} pages in {elapsed_time:.1f}s ({pages_per_second:.2f} pages/s)")
                
            # Update statistics
            self.stats["total_errors"] += error_count
            
        except Exception as e:
            logger.error(f"Error in site mapping for {domain}: {str(e)}")
            self.mapping_status[domain] = "error"
            self.stats["total_errors"] += 1
    
    def fetch_website_content(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a website with caching.
        
        Args:
            url: The URL to fetch content from
            
        Returns:
            HTML content as string or None if failed
        """
        # Check cache first
        if url in self.content_cache:
            return self.content_cache[url]
        
        try:
            # Apply rate limiting
            domain = urlparse(url).netloc
            self._apply_rate_limiting(domain)
            
            # Make the request
            response = self.session.get(url, timeout=15)
            
            if response.status_code >= 400:
                logger.error(f"Error fetching {url}: Status code {response.status_code}")
                return None
            
            # Try to determine encoding
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding
            
            html_content = response.text
            
            # Basic validation of HTML content
            if not html_content or len(html_content) < 100:
                logger.warning(f"Received suspiciously small content from {url}: {len(html_content)} bytes")
                if len(html_content) > 0:
                    logger.warning(f"Content preview: {html_content[:100]}...")
            
            # Cache the content
            self.content_cache[url] = html_content
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {str(e)}")
            return None
    
    def find_relevant_pages(self, topic: str, domain: str = None) -> List[Dict[str, Any]]:
        """
        Find pages in the site map that might contain information about a topic.
        
        Args:
            topic: The topic to search for
            domain: Optional domain to search in (if None, search in all mapped domains)
            
        Returns:
            List of pages with relevance information
        """
        results = []
        
        # Convert topic to keywords
        topic_keywords = self._extract_keywords(topic)
        topic_words = [word.lower() for word in re.findall(r'\w+', topic.lower())]
        
        # Determine which domains to search
        domains_to_search = [domain] if domain else self.site_maps.keys()
        
        # Search in each domain
        for current_domain in domains_to_search:
            if current_domain not in self.site_maps:
                continue
                
            for url, page_info in self.site_maps[current_domain].items():
                relevance = 0
                
                # Check title relevance (highest weight)
                title = page_info.get("title", "")
                if title:
                    # Direct keyword matches in title
                    for word in topic_words:
                        if word in title.lower():
                            relevance += 8  # High weight for title matches
                    
                    # Keyword overlap in title
                    title_keywords = self._extract_keywords(title)
                    title_overlap = len(topic_keywords.intersection(title_keywords))
                    relevance += title_overlap * 5
                
                # Check URL relevance
                url_lower = url.lower()
                for word in topic_words:
                    if word in url_lower:
                        relevance += 3  # Medium weight for URL matches
                
                # Check heading relevance (high weight)
                for heading in page_info.get("headings", []):
                    for word in topic_words:
                        if word in heading.lower():
                            relevance += 6  # High weight for heading matches
                
                # Check keyword relevance (from page content)
                page_keywords = set(page_info.get("keywords", []))
                keyword_overlap = len(topic_keywords.intersection(page_keywords))
                relevance += keyword_overlap * 2  # Lower weight for general content matches
                
                # Only include pages with some relevance
                if relevance > 0:
                    results.append({
                        "url": url,
                        "title": page_info.get("title", ""),
                        "relevance": relevance,
                        "matched_keywords": list(topic_keywords.intersection(page_keywords))
                    })
        
        # Sort by relevance score, descending
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results
    
    def get_site_map(self, domain: str = None) -> Dict[str, Any]:
        """
        Get the complete site map for a domain.
        
        Args:
            domain: The domain to get the site map for (if None, return all site maps)
            
        Returns:
            Dictionary with site map information
        """
        if domain:
            return self.site_maps.get(domain, {})
        else:
            return self.site_maps
    
    def get_site_structure_as_tree(self, domain: str) -> Dict[str, Any]:
        """
        Organize the site map into a hierarchical tree structure.
        
        Args:
            domain: The domain to organize
            
        Returns:
            Tree structure of the website
        """
        if domain not in self.site_maps:
            return {}
            
        site_map = self.site_maps[domain]
        base_url = f"https://{domain}"
        
        # Find the root/home page
        root_url = base_url
        if root_url not in site_map:
            # Try with trailing slash
            root_url = f"{base_url}/"
            if root_url not in site_map:
                # Try to find another page that could be the home page
                for url in site_map:
                    if urlparse(url).path in ['', '/', '/index.html', '/home']:
                        root_url = url
                        break
        
        # Create tree structure
        tree = {
            "url": root_url,
            "title": site_map.get(root_url, {}).get("title", domain),
            "children": {}
        }
        
        # Group pages by path structure
        for url in site_map:
            if url == root_url:
                continue
                
            parsed_url = urlparse(url)
            path = parsed_url.path.strip('/')
            
            if not path:
                continue
                
            path_parts = path.split('/')
            
            # Add to tree structure
            current_level = tree["children"]
            current_path = ""
            
            for i, part in enumerate(path_parts):
                current_path = f"{current_path}/{part}" if current_path else part
                full_path = f"{base_url}/{current_path}"
                
                if part not in current_level:
                    current_level[part] = {
                        "url": full_path,
                        "title": site_map.get(full_path, {}).get("title", part),
                        "children": {}
                    }
                
                if i < len(path_parts) - 1:
                    current_level = current_level[part]["children"]
        
        return tree
    
    def export_sitemap_xml(self, domain: str) -> str:
        """
        Generate a sitemap.xml content for the mapped site.
        
        Args:
            domain: The domain to generate sitemap for
            
        Returns:
            String with sitemap.xml content
        """
        if domain not in self.site_maps:
            return ""
            
        # XML header
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        # Add each URL
        for url in self.site_maps[domain]:
            lastmod = time.strftime('%Y-%m-%d', time.localtime(self.site_maps[domain][url].get("crawled_at", time.time())))
            xml += '  <url>\n'
            xml += f'    <loc>{url}</loc>\n'
            xml += f'    <lastmod>{lastmod}</lastmod>\n'
            xml += '    <changefreq>monthly</changefreq>\n'
            xml += '  </url>\n'
        
        xml += '</urlset>'
        return xml
    
    def generate_report(self, domain: str) -> Dict[str, Any]:
        """
        Generate a comprehensive report about the website structure.
        
        Args:
            domain: The domain to generate report for
            
        Returns:
            Dictionary with report data
        """
        if domain not in self.site_maps:
            return {"error": "Domain not mapped"}
            
        site_map = self.site_maps[domain]
        
        # Basic stats
        total_pages = len(site_map)
        
        # Collect all links
        all_links = []
        internal_links = 0
        external_links = 0
        
        for url, page_info in site_map.items():
            for link in page_info.get("links", []):
                link_url = link.get("url", "")
                if urlparse(link_url).netloc == domain:
                    internal_links += 1
                else:
                    external_links += 1
                all_links.append(link_url)
        
        # Get unique links
        unique_links = len(set(all_links))
        
        # Analyze site depth
        max_depth = 0
        for url in site_map:
            depth = len(urlparse(url).path.strip('/').split('/'))
            max_depth = max(max_depth, depth)
        
        # Identify common sections/topics
        all_keywords = []
        for url, page_info in site_map.items():
            all_keywords.extend(page_info.get("keywords", []))
        
        # Count keyword frequency
        keyword_counts = {}
        for keyword in all_keywords:
            if keyword in keyword_counts:
                keyword_counts[keyword] += 1
            else:
                keyword_counts[keyword] = 1
        
        # Get top keywords
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Generate report
        report = {
            "domain": domain,
            "url_count": total_pages,
            "internal_links": internal_links,
            "external_links": external_links,
            "unique_links": unique_links,
            "max_depth": max_depth,
            "top_keywords": top_keywords,
            "most_linked_pages": self._get_most_linked_pages(domain),
            "orphaned_pages": self._get_orphaned_pages(domain),
            "mapping_status": self.mapping_status.get(domain, "unknown"),
            "generated_at": time.time()
        }
        
        return report
    
    def _normalize_url(self, url: str) -> str:
        """Normalize a URL by adding scheme if missing."""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Remove trailing slash if present
        if url.endswith('/') and len(url) > 8:
            url = url[:-1]
            
        return url
    
    def _apply_rate_limiting(self, domain: str) -> None:
        """Apply rate limiting for a domain."""
        with self.rate_limit_lock:
            current_time = time.time()
            if domain in self.last_request_time:
                elapsed = current_time - self.last_request_time[domain]
                if elapsed < self.request_interval:
                    sleep_time = self.request_interval - elapsed
                    time.sleep(sleep_time)
            
            # Update the last request time
            self.last_request_time[domain] = time.time()
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the title of the website."""
        if soup.title:
            return soup.title.string.strip() if soup.title.string else "Untitled"
        else:
            # Try to find an h1 as fallback
            h1 = soup.find('h1')
            if h1 and h1.text:
                return h1.text.strip()
        return "Untitled"
    
    def _extract_meta_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta information from the website."""
        meta_info = {}
        
        # Extract description
        description = soup.find('meta', attrs={'name': 'description'})
        if description and 'content' in description.attrs:
            meta_info['description'] = description['content']
            
        # Extract keywords
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        if keywords and 'content' in keywords.attrs:
            meta_info['keywords'] = keywords['content']
            
        # Extract Open Graph metadata
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        if og_title and 'content' in og_title.attrs:
            meta_info['og_title'] = og_title['content']
            
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and 'content' in og_desc.attrs:
            meta_info['og_description'] = og_desc['content']
            
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image and 'content' in og_image.attrs:
            meta_info['og_image'] = og_image['content']
            
        return meta_info
    
    def _extract_navigation_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract navigation links from the website."""
        nav_links = []
        
        # Look for navigation elements by semantic tags
        nav_elements = soup.find_all(['nav', 'header', 'div', 'ul'], class_=lambda c: c and any(nav_term in str(c).lower() for nav_term in ['nav', 'menu', 'header', 'topbar', 'toolbar', 'main-menu']))
        
        # Process each navigation element
        for nav in nav_elements:
            # Determine section name
            section_name = self._determine_section_name(nav)
            
            # Extract links from this navigation section
            links = nav.find_all('a', href=True)
            for link in links:
                # Skip if it's a likely non-navigation link
                if self._should_skip_link(link):
                    continue
                    
                href = link['href']
                # Normalize URL
                if not href.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'javascript:')):
                    href = urljoin(base_url, href)
                    
                # Skip anchors, javascript, etc.
                if href.startswith(('mailto:', 'tel:', 'javascript:')):
                    continue
                    
                # Skip if it's the same as base_url
                if href == base_url or href == base_url + '/':
                    continue
                    
                # Get link text
                link_text = link.get_text().strip()
                if not link_text:
                    # Try to get text from child elements like images
                    img = link.find('img')
                    if img and img.get('alt'):
                        link_text = img.get('alt').strip()
                    else:
                        # Use link URL as last resort
                        link_text = href.split('/')[-1].replace('-', ' ').replace('_', ' ').capitalize()
                
                # Add to navigation links if not already present
                link_info = {
                    "text": link_text,
                    "url": href,
                    "section": section_name,
                    "is_external": not href.startswith(base_url) and href.startswith(('http://', 'https://'))
                }
                
                # Check if link already exists to avoid duplicates
                if not any(existing['url'] == href for existing in nav_links):
                    nav_links.append(link_info)
        
        return nav_links
    
    def _determine_section_name(self, nav_element: BeautifulSoup) -> str:
        """Determine a meaningful name for a navigation section."""
        # Check for aria-label
        if 'aria-label' in nav_element.attrs:
            return nav_element['aria-label'].strip()
            
        # Check for title attribute
        if 'title' in nav_element.attrs:
            return nav_element['title'].strip()
            
        # Check for heading elements that might describe the navigation
        heading = nav_element.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if heading and heading.text.strip():
            return heading.text.strip()
            
        # Look at class names for hints
        if 'class' in nav_element.attrs:
            class_text = ' '.join(nav_element['class'])
            for nav_type in ['main', 'primary', 'secondary', 'footer', 'sidebar', 'utility', 'social']:
                if nav_type in class_text.lower():
                    return f"{nav_type.capitalize()} Navigation"
        
        # Look at id attribute
        if 'id' in nav_element.attrs:
            id_text = nav_element['id']
            for nav_type in ['main', 'primary', 'secondary', 'footer', 'sidebar', 'utility', 'social']:
                if nav_type in id_text.lower():
                    return f"{nav_type.capitalize()} Navigation"
                    
        # Default by location
        if nav_element.find_parent('header'):
            return "Header Navigation"
        elif nav_element.find_parent('footer'):
            return "Footer Navigation"
        elif nav_element.find_parent('aside'):
            return "Sidebar Navigation"
            
        return "Main Navigation"
    
    def _should_skip_link(self, link: BeautifulSoup) -> bool:
        """Determine if a link should be skipped in navigation collection."""
        # Skip links with no text content or very short text
        link_text = link.get_text().strip()
        if not link_text or len(link_text) <= 1:
            # Only keep if it has an image with alt text
            if link.find('img', alt=lambda alt: alt and len(alt.strip()) > 1):
                return False
            return True
            
        # Skip likely utility links
        skip_patterns = ['login', 'sign in', 'sign up', 'register', 'log in', 
                        'cart', 'basket', 'bag', 'checkout', 'account', 'profile',
                        'search', 'language', 'cookie', 'privacy', 'terms']
                        
        if any(pattern in link_text.lower() for pattern in skip_patterns):
            return False  # Actually include these as they're useful navigation points
            
        # Skip links that are likely social media
        social_patterns = ['facebook', 'twitter', 'instagram', 'linkedin', 'youtube',
                          'pinterest', 'tiktok', 'snapchat', 'whatsapp', 'telegram']
                          
        if any(pattern in link_text.lower() for pattern in social_patterns):
            return True
            
        return False
    
    def _extract_additional_navigation(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract additional navigation links not in traditional nav elements."""
        additional_links = []
        
        # Look for footer links
        footer = soup.find('footer')
        if footer:
            section_name = "Footer Links"
            links = footer.find_all('a', href=True)
            for link in links:
                href = link['href']
                if not href.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'javascript:')):
                    href = urljoin(base_url, href)
                
                # Skip certain types of links
                if href.startswith(('mailto:', 'tel:', 'javascript:')) or '#' in href:
                    continue
                    
                link_text = link.get_text().strip()
                if not link_text:
                    continue
                    
                link_info = {
                    "text": link_text,
                    "url": href,
                    "section": section_name,
                    "is_external": not href.startswith(base_url) and href.startswith(('http://', 'https://'))
                }
                
                additional_links.append(link_info)
                
        # Look for sidebar links
        sidebar = soup.find(['aside', 'div'], class_=lambda c: c and any(term in str(c).lower() for term in ['sidebar', 'side-bar', 'side_bar', 'sidenav', 'side-nav']))
        if sidebar:
            section_name = "Sidebar Links"
            links = sidebar.find_all('a', href=True)
            for link in links:
                href = link['href']
                if not href.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'javascript:')):
                    href = urljoin(base_url, href)
                
                if href.startswith(('mailto:', 'tel:', 'javascript:')) or '#' in href:
                    continue
                    
                link_text = link.get_text().strip()
                if not link_text:
                    continue
                    
                link_info = {
                    "text": link_text,
                    "url": href,
                    "section": section_name,
                    "is_external": not href.startswith(base_url) and href.startswith(('http://', 'https://'))
                }
                
                additional_links.append(link_info)
        
        # Look for sitemap link
        sitemap_link = soup.find('a', href=lambda href: href and 'sitemap' in href.lower())
        if sitemap_link and 'href' in sitemap_link.attrs:
            href = sitemap_link['href']
            if not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
                
            additional_links.append({
                "text": "Sitemap",
                "url": href,
                "section": "Site Utilities",
                "is_external": False
            })
            
        return additional_links
    
    def _extract_content_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract main content sections from the website."""
        content_sections = []
        
        # Look for main content area
        main_content = soup.find(['main', 'article', 'div'], id=lambda i: i and 'content' in i.lower())
        if not main_content:
            main_content = soup.find(['main', 'article', 'div'], class_=lambda c: c and 'content' in str(c).lower())
        
        # If no explicit main content, use the body
        if not main_content:
            main_content = soup.body
            
        if main_content:
            # Find direct heading sections
            headings = main_content.find_all(['h1', 'h2', 'h3'])
            for heading in headings:
                # Skip duplicate or invisible headings
                if not heading.text.strip() or heading.parent.name == 'option':
                    continue
                    
                # Extract content following the heading
                content = ""
                current = heading.next_sibling
                while current and current.name != 'h1' and current.name != 'h2' and current.name != 'h3':
                    if isinstance(current, str):
                        content += current.strip() + " "
                    elif current.name in ['p', 'div', 'span', 'ul', 'ol', 'blockquote', 'table']:
                        content += current.get_text().strip() + " "
                    current = current.next_sibling
                    
                content = content.strip()
                if content:
                    section = {
                        "heading": heading.get_text().strip(),
                        "content": content,
                        "length": len(content)
                    }
                    content_sections.append(section)
                    
            # If no sections were created, try a different approach
            if not content_sections:
                # Look for paragraph blocks
                paragraphs = main_content.find_all('p')
                current_section = {"heading": "", "content": "", "length": 0}
                
                for p in paragraphs:
                    p_text = p.get_text().strip()
                    if p_text:
                        if not current_section["content"]:
                            # This is the first paragraph, use as heading if short
                            if len(p_text) < 100:
                                current_section["heading"] = p_text
                            else:
                                current_section["content"] = p_text
                                current_section["length"] = len(p_text)
                        else:
                            current_section["content"] += " " + p_text
                            current_section["length"] += len(p_text)
                            
                            # If section is long enough, save it and start a new one
                            if current_section["length"] > 500:
                                content_sections.append(current_section)
                                current_section = {"heading": "", "content": "", "length": 0}
                                
                # Add the last section if it has content
                if current_section["content"] and current_section["length"] > 0:
                    content_sections.append(current_section)
        
        return content_sections
    
    def _extract_forms(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract forms from the website."""
        forms_data = []
        forms = soup.find_all('form')
        
        for form in forms:
            form_info = {
                "action": form.get('action', ''),
                "method": form.get('method', 'get').upper(),
                "fields": []
            }
            
            # Try to determine form purpose
            form_id = form.get('id', '').lower()
            form_class = ' '.join(form.get('class', [])).lower()
            form_name = form.get('name', '').lower()
            
            if any(term in form_id or term in form_class or term in form_name 
                  for term in ['search', 'find']):
                form_info['purpose'] = 'search'
            elif any(term in form_id or term in form_class or term in form_name 
                    for term in ['login', 'signin', 'log-in', 'sign-in']):
                form_info['purpose'] = 'login'
            elif any(term in form_id or term in form_class or term in form_name 
                    for term in ['register', 'signup', 'sign-up', 'create-account']):
                form_info['purpose'] = 'registration'
            elif any(term in form_id or term in form_class or term in form_name 
                    for term in ['contact', 'feedback', 'message']):
                form_info['purpose'] = 'contact'
            elif any(term in form_id or term in form_class or term in form_name 
                    for term in ['newsletter', 'subscribe']):
                form_info['purpose'] = 'newsletter'
            else:
                form_info['purpose'] = 'unknown'
                
            # Extract form fields
            for field in form.find_all(['input', 'select', 'textarea']):
                if field.name == 'input' and field.get('type') in ['submit', 'button', 'image', 'reset']:
                    continue
                    
                field_info = {
                    "type": field.name if field.name != 'input' else field.get('type', 'text'),
                    "name": field.get('name', ''),
                    "placeholder": field.get('placeholder', ''),
                    "required": field.has_attr('required') or field.get('required') == 'required'
                }
                
                if field.name == 'select':
                    field_info['options'] = [opt.get_text().strip() for opt in field.find_all('option')]
                    
                form_info['fields'].append(field_info)
                
            forms_data.append(form_info)
            
        return forms_data
    
    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract social media links from the website."""
        social_links = []
        social_patterns = {
            'facebook': ['facebook.com', 'fb.com', 'fb.me', 'facebook'],
            'twitter': ['twitter.com', 'x.com', 't.co', 'twitter'],
            'instagram': ['instagram.com', 'instagr.am', 'instagram'],
            'linkedin': ['linkedin.com', 'lnkd.in', 'linkedin'],
            'youtube': ['youtube.com', 'youtu.be', 'youtube'],
            'pinterest': ['pinterest.com', 'pin.it', 'pinterest'],
            'tiktok': ['tiktok.com', 'tiktok'],
            'github': ['github.com', 'github']
        }
        
        # Find all links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
                
            # Check if it's a social media link
            for platform, patterns in social_patterns.items():
                if any(pattern in href.lower() for pattern in patterns):
                    # Try to get link text
                    link_text = link.get_text().strip()
                    if not link_text:
                        link_text = f"Follow on {platform.capitalize()}"
                        
                    social_links.append({
                        "platform": platform,
                        "url": href,
                        "text": link_text
                    })
                    
        return social_links
    
    def _extract_keywords(self, text: str, min_length: int = 3, max_words: int = 100) -> Set[str]:
        """Extract keywords from text."""
        # Simple tokenization, remove punctuation, convert to lowercase
        words = re.findall(r'\w+', text.lower())
        
        # Filter words by length
        words = [word for word in words if len(word) >= min_length]
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'about', 'as', 'into', 'like', 'through', 'after', 'over', 'between',
            'out', 'against', 'during', 'before', 'because', 'that', 'then', 'than', 'this',
            'these', 'those', 'there', 'here', 'when', 'where', 'which', 'who', 'whom', 'what'
        }
        
        filtered_words = [word for word in words if word not in stop_words]
        
        # Get word frequency
        word_freq = {}
        for word in filtered_words:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Return top words as a set
        return set(word for word, _ in sorted_words[:max_words])
    
    def _get_most_linked_pages(self, domain: str) -> List[Dict[str, Any]]:
        """Get the most linked-to pages in the site map."""
        if domain not in self.site_maps:
            return []
            
        # Count incoming links for each page
        incoming_links = {}
        
        for url, page_info in self.site_maps[domain].items():
            for link in page_info.get("links", []):
                link_url = link.get("url", "")
                if urlparse(link_url).netloc == domain:
                    if link_url in incoming_links:
                        incoming_links[link_url] += 1
                    else:
                        incoming_links[link_url] = 1
        
        # Sort pages by incoming link count
        most_linked = sorted(incoming_links.items(), key=lambda x: x[1], reverse=True)
        
        # Format result
        result = []
        for url, count in most_linked[:10]:  # Top 10
            page_info = self.site_maps[domain].get(url, {})
            result.append({
                "url": url,
                "title": page_info.get("title", url),
                "incoming_links": count
            })
            
        return result
    
    def _get_orphaned_pages(self, domain: str) -> List[Dict[str, Any]]:
        """Get pages that have no incoming links from other pages."""
        if domain not in self.site_maps:
            return []
            
        # Find all pages with incoming links
        pages_with_links = set()
        
        for url, page_info in self.site_maps[domain].items():
            for link in page_info.get("links", []):
                link_url = link.get("url", "")
                if urlparse(link_url).netloc == domain:
                    pages_with_links.add(link_url)
        
        # Find orphaned pages (pages in site map without incoming links)
        orphaned = []
        
        for url in self.site_maps[domain]:
            if url not in pages_with_links:
                orphaned.append({
                    "url": url,
                    "title": self.site_maps[domain][url].get("title", url)
                })
                
        return orphaned

# Adapter functions to maintain compatibility with existing UI

def generate_sitemap(url: str, max_depth: int = 3) -> Dict[str, Any]:
    """
    Generate a sitemap for the given URL using WebsiteSitemapExtractor.
    
    Args:
        url: The URL to analyze
        max_depth: Maximum depth to crawl
        
    Returns:
        Dictionary containing site structure information
    """
    logger.info(f"Starting site structure analysis for URL: {url}")
    
    try:
        # Get settings from session state if available
        import streamlit as st
        requests_per_minute = st.session_state.get('requests_per_minute', 30)
        max_pages = st.session_state.get('max_pages', 50)
        
        # Create extractor instance
        extractor = WebsiteSitemapExtractor(
            requests_per_minute=requests_per_minute,
            max_pages=max_pages,
            max_depth=max_depth
        )
        
        # Extract initial sitemap
        site_data = extractor.extract_sitemap(url, background_mapping=True)
        
        # Transform the data to match the expected format by the UI
        domain = urlparse(url).netloc
        
        # Prepare the structure to match existing UI expectations
        result = {
            "url": url,
            "title": site_data.get("title", ""),
            "meta_info": site_data.get("meta_info", {}),
            "navigation_links": site_data.get("navigation_links", []),
            "content_sections": site_data.get("content_sections", []),
            "sitemap_structure": {
                "hostname": domain,
                "linksByDepth": {},
                "totalUniqueLinks": 0,
            },
            "internal_link_count": 0,
            "external_link_count": 0,
        }
        
        # Store the extractor in a global dictionary for later use
        if not hasattr(generate_sitemap, '_extractors'):
            generate_sitemap._extractors = {}
        
        generate_sitemap._extractors[domain] = extractor
        
        # Get current site map data (even if incomplete)
        site_map = extractor.get_site_map(domain)
        
        # Count links by depth for sitemap structure
        links_by_depth = {}
        internal_links = 0
        external_links = 0
        
        for url_data in site_map.values():
            for link in url_data.get("links", []):
                # Determine if it's internal or external
                if link.get("is_external", False):
                    external_links += 1
                else:
                    internal_links += 1
                    
                    # Process depth
                    link_url = link.get("url", "")
                    path = urlparse(link_url).path.strip('/')
                    depth = 0 if not path else len(path.split('/'))
                    
                    if str(depth) not in links_by_depth:
                        links_by_depth[str(depth)] = []
                    
                    # Add to depth list if not already there
                    if not any(item.get("url") == link_url for item in links_by_depth[str(depth)]):
                        links_by_depth[str(depth)].append({
                            "url": link_url,
                            "path": path,
                            "text": link.get("text", "")
                        })
        
        # Update result with link information
        result["sitemap_structure"]["linksByDepth"] = links_by_depth
        result["sitemap_structure"]["totalUniqueLinks"] = len(set(u for d in links_by_depth.values() for u in [item["url"] for item in d]))
        result["internal_link_count"] = internal_links
        result["external_link_count"] = external_links
        
        # Check if we have any extracted forms
        if site_data.get("forms"):
            result["forms"] = site_data.get("forms")
        
        # Check if we have any social links
        if site_data.get("social_links"):
            result["social_links"] = site_data.get("social_links")
        
        logger.info(f"Site structure analysis completed for URL: {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing site structure: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "url": url,
            "error": str(e),
            "title": "Error analyzing site",
            "meta_info": {},
            "navigation_links": [],
            "content_sections": [],
            "all_links": [],
            "sitemap_structure": {"hostname": "", "linksByDepth": {}, "totalUniqueLinks": 0},
            "internal_link_count": 0,
            "external_link_count": 0,
        }

