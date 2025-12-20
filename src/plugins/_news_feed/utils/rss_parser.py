"""
RSS/Atom Feed Parser Utility
Handles parsing of RSS 2.0 and Atom feeds
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
import re
from html import unescape
import urllib.request
import urllib.error
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class FeedParser:
    """Parser for RSS 2.0 and Atom feeds"""

    # Namespace definitions
    NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'media': 'http://search.yahoo.com/mrss/',
    }

    def __init__(self):
        self.feed_type = None
        self.feed_data = {}
        self.items = []

    def parse_feed(self, url: str, timeout: int = 30) -> Tuple[Dict, List[Dict]]:
        """
        Parse a feed from URL
        Returns: (feed_info, items)
        """
        try:
            # Fetch the feed content
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'AgentPilot News Reader/1.0',
                    'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*'
                }
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read()
                encoding = response.headers.get_content_charset() or 'utf-8'
                xml_content = content.decode(encoding, errors='ignore')

            return self.parse_feed_content(xml_content, url)

        except urllib.error.URLError as e:
            logger.error(f"Failed to fetch feed from {url}: {e}")
            raise Exception(f"Failed to fetch feed: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing feed from {url}: {e}")
            raise Exception(f"Error parsing feed: {str(e)}")

    def parse_feed_content(self, xml_content: str, source_url: str = "") -> Tuple[Dict, List[Dict]]:
        """
        Parse feed content from XML string
        Returns: (feed_info, items)
        """
        try:
            # Parse XML
            root = ET.fromstring(xml_content)

            # Detect feed type
            if root.tag == 'rss' or root.tag.endswith('}rss'):
                return self._parse_rss(root, source_url)
            elif root.tag == '{http://www.w3.org/2005/Atom}feed' or root.tag == 'feed':
                return self._parse_atom(root, source_url)
            else:
                # Try to detect by looking for channel or entry elements
                if root.find('.//channel') is not None:
                    return self._parse_rss(root, source_url)
                elif root.find('.//entry') is not None or root.find('.//{http://www.w3.org/2005/Atom}entry') is not None:
                    return self._parse_atom(root, source_url)
                else:
                    raise ValueError(f"Unknown feed format: {root.tag}")

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise Exception(f"Invalid XML format: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing feed content: {e}")
            raise

    def _parse_rss(self, root: ET.Element, source_url: str) -> Tuple[Dict, List[Dict]]:
        """Parse RSS 2.0 feed"""
        feed_info = {'type': 'rss', 'source_url': source_url}
        items = []

        channel = root.find('.//channel')
        if channel is None:
            raise ValueError("No channel element found in RSS feed")

        # Parse feed metadata
        feed_info['title'] = self._get_text(channel, 'title', '')
        feed_info['description'] = self._get_text(channel, 'description', '')
        feed_info['link'] = self._get_text(channel, 'link', '')
        feed_info['language'] = self._get_text(channel, 'language', '')
        feed_info['last_build_date'] = self._get_text(channel, 'lastBuildDate', '')

        # Parse items
        for item in channel.findall('item'):
            entry = {}
            entry['title'] = self._clean_text(self._get_text(item, 'title', ''))
            entry['link'] = self._get_text(item, 'link', '')
            entry['description'] = self._clean_text(self._get_text(item, 'description', ''))
            entry['guid'] = self._get_text(item, 'guid', entry['link'])  # Use link as fallback
            entry['pub_date'] = self._parse_date(self._get_text(item, 'pubDate', ''))
            entry['author'] = self._get_text(item, 'author', '') or self._get_text(item, '{http://purl.org/dc/elements/1.1/}creator', '')

            # Try to get full content
            content = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
            if content is not None and content.text:
                entry['content'] = self._clean_text(content.text)
            else:
                entry['content'] = entry['description']

            # Get enclosures (media)
            enclosure = item.find('enclosure')
            if enclosure is not None:
                entry['enclosure'] = {
                    'url': enclosure.get('url', ''),
                    'type': enclosure.get('type', ''),
                    'length': enclosure.get('length', '')
                }

            # Categories/tags
            categories = item.findall('category')
            if categories:
                entry['categories'] = [cat.text for cat in categories if cat.text]

            items.append(entry)

        return feed_info, items

    def _parse_atom(self, root: ET.Element, source_url: str) -> Tuple[Dict, List[Dict]]:
        """Parse Atom feed"""
        feed_info = {'type': 'atom', 'source_url': source_url}
        items = []

        # Handle namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        # Parse feed metadata
        feed_info['title'] = self._get_text(root, '{http://www.w3.org/2005/Atom}title', '')
        feed_info['description'] = self._get_text(root, '{http://www.w3.org/2005/Atom}subtitle', '')

        # Get feed link
        link_elem = root.find("{http://www.w3.org/2005/Atom}link[@rel='alternate']")
        if link_elem is None:
            link_elem = root.find('{http://www.w3.org/2005/Atom}link')
        feed_info['link'] = link_elem.get('href', '') if link_elem is not None else ''

        feed_info['updated'] = self._get_text(root, '{http://www.w3.org/2005/Atom}updated', '')

        # Parse entries
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            item = {}
            item['title'] = self._clean_text(self._get_text(entry, '{http://www.w3.org/2005/Atom}title', ''))

            # Get entry link
            link_elem = entry.find("{http://www.w3.org/2005/Atom}link[@rel='alternate']")
            if link_elem is None:
                link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
            item['link'] = link_elem.get('href', '') if link_elem is not None else ''

            item['guid'] = self._get_text(entry, '{http://www.w3.org/2005/Atom}id', item['link'])

            # Get summary or content
            summary = self._get_text(entry, '{http://www.w3.org/2005/Atom}summary', '')
            content_elem = entry.find('{http://www.w3.org/2005/Atom}content')
            if content_elem is not None and content_elem.text:
                item['content'] = self._clean_text(content_elem.text)
                item['description'] = self._clean_text(summary) if summary else item['content'][:200] + '...'
            else:
                item['description'] = self._clean_text(summary)
                item['content'] = item['description']

            # Dates
            published = self._get_text(entry, '{http://www.w3.org/2005/Atom}published', '')
            updated = self._get_text(entry, '{http://www.w3.org/2005/Atom}updated', '')
            item['pub_date'] = self._parse_date(published or updated)

            # Author
            author_elem = entry.find('{http://www.w3.org/2005/Atom}author')
            if author_elem is not None:
                item['author'] = self._get_text(author_elem, '{http://www.w3.org/2005/Atom}name', '')
            else:
                item['author'] = ''

            # Categories
            categories = entry.findall('{http://www.w3.org/2005/Atom}category')
            if categories:
                item['categories'] = [cat.get('term', '') for cat in categories if cat.get('term')]

            items.append(item)

        return feed_info, items

    def _get_text(self, element: ET.Element, tag: str, default: str = '') -> str:
        """Safely get text content from element"""
        if element is None:
            return default
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return default

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ''

        # Unescape HTML entities
        text = unescape(text)

        # Remove HTML tags (basic)
        text = re.sub(r'<[^>]+>', '', text)

        # Normalize whitespace
        text = ' '.join(text.split())

        return text.strip()

    def _parse_date(self, date_str: str) -> str:
        """Parse various date formats to ISO format"""
        if not date_str:
            return ''

        # Common date formats in feeds
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %Z',    # RFC 822
            '%a, %d %b %Y %H:%M:%S %z',    # RFC 822 with timezone
            '%Y-%m-%dT%H:%M:%S%z',          # ISO 8601 with timezone
            '%Y-%m-%dT%H:%M:%SZ',           # ISO 8601 UTC
            '%Y-%m-%d %H:%M:%S',            # Simple datetime
            '%Y-%m-%d',                     # Simple date
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat()
            except ValueError:
                continue

        # If no format matches, return original string
        logger.debug(f"Could not parse date: {date_str}")
        return date_str


def validate_feed_url(url: str) -> bool:
    """Validate if URL is a valid feed URL"""
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def fetch_and_parse_feed(url: str, timeout: int = 30) -> Tuple[Dict, List[Dict]]:
    """
    Convenience function to fetch and parse a feed
    Returns: (feed_info, items)
    """
    if not validate_feed_url(url):
        raise ValueError(f"Invalid feed URL: {url}")

    parser = FeedParser()
    return parser.parse_feed(url, timeout)


# Test function for development
if __name__ == "__main__":
    # Test with some common feed URLs
    test_urls = [
        "https://news.ycombinator.com/rss",
        "https://feeds.bbci.co.uk/news/rss.xml",
    ]

    for url in test_urls:
        try:
            feed_info, items = fetch_and_parse_feed(url)
            print(f"\nFeed: {feed_info.get('title', 'Unknown')}")
            print(f"Type: {feed_info.get('type', 'Unknown')}")
            print(f"Items: {len(items)}")
            if items:
                print(f"Latest: {items[0].get('title', 'No title')}")
        except Exception as e:
            print(f"Error testing {url}: {e}")