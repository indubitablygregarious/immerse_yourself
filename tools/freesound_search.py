#!/usr/bin/env python3
"""
Freesound.org search tool - searches for sounds and returns URLs, descriptions, and tags.

Usage:
    python3 tools/freesound_search.py "keywords here"
    python3 tools/freesound_search.py "outdoor crowd ambience"
    python3 tools/freesound_search.py "rope rigging ship"
"""

import sys
import re
import urllib.request
import urllib.parse
from html import unescape


def search_freesound(keywords: str, max_results: int = 10) -> list:
    """
    Search freesound.org for sounds matching keywords.

    Args:
        keywords: Search terms (e.g., "outdoor crowd ambience")
        max_results: Maximum number of results to return

    Returns:
        List of dicts with url, title, description, tags, duration
    """
    # Build search URL
    query = urllib.parse.quote_plus(keywords)
    url = f"https://freesound.org/search/?q={query}"

    # Fetch the page
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching search results: {e}", file=sys.stderr)
        return []

    results = []
    seen_urls = set()

    # Find all sound links: /people/USER/sounds/ID/
    sound_pattern = re.compile(
        r'<a[^>]+href="(/people/([^"]+)/sounds/(\d+)/)"[^>]*>([^<]+)</a>',
        re.IGNORECASE
    )

    # Find all tags: /browse/tags/TAGNAME/
    tag_pattern = re.compile(r'href="/browse/tags/([^"/]+)/"', re.IGNORECASE)

    # Process HTML in chunks around each sound link
    for match in sound_pattern.finditer(html):
        href, user, sound_id, title = match.groups()
        full_url = f'https://freesound.org{href}'

        # Skip duplicates
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Clean up title
        title = unescape(title.strip())

        # Skip navigation/non-sound links
        if not title or title in ['Download', 'Edit', 'Delete', 'Similar sounds']:
            continue

        # Get context around this match to find tags
        start = max(0, match.start() - 500)
        end = min(len(html), match.end() + 2000)
        context = html[start:end]

        # Extract tags from context
        tags = list(set(tag_pattern.findall(context)))[:10]

        # Try to find description - look for text after the title
        desc = ""
        desc_match = re.search(
            rf'{re.escape(title)}</a>\s*</[^>]+>\s*([^<]+)',
            context,
            re.IGNORECASE
        )
        if desc_match:
            desc = unescape(desc_match.group(1).strip())

        results.append({
            'user': user,
            'id': sound_id,
            'url': full_url,
            'title': title,
            'description': desc[:200] if desc else '',
            'tags': tags,
            'duration': ''
        })

        if len(results) >= max_results:
            break

    return results


def format_results(results: list) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."

    output = []
    for i, r in enumerate(results, 1):
        output.append(f"\n{'='*60}")
        output.append(f"[{i}] {r['title']}")
        output.append(f"    URL: {r['url']}")
        output.append(f"    By: {r['user']}")
        if r['duration']:
            output.append(f"    Duration: {r['duration']}")
        if r['description']:
            desc = r['description'][:150] + "..." if len(r['description']) > 150 else r['description']
            output.append(f"    Description: {desc}")
        if r['tags']:
            output.append(f"    Tags: {', '.join(r['tags'][:10])}")

    return '\n'.join(output)


def format_yaml(results: list) -> str:
    """Format results as YAML snippet for env_conf files."""
    if not results:
        return "# No results found"

    output = ["# Freesound.org sounds:"]
    for r in results:
        comment = r['title']
        if r['duration']:
            comment += f" ({r['duration']})"
        output.append(f"      # {comment}")
        output.append(f"      - url: \"{r['url']}\"")
        output.append(f"        volume: 50")
        output.append("")

    return '\n'.join(output)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    keywords = ' '.join(sys.argv[1:])
    print(f"Searching freesound.org for: {keywords}")
    print(f"Search URL: https://freesound.org/search/?q={urllib.parse.quote_plus(keywords)}")

    results = search_freesound(keywords, max_results=10)

    print(format_results(results))
    print("\n" + "="*60)
    print("YAML format for env_conf:")
    print(format_yaml(results[:5]))
