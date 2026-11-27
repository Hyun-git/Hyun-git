#!/usr/bin/env python3
"""Update the profile's recent-writing list from its public Atom feed."""

from datetime import datetime, timezone
from html import unescape
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

FEED_URL = "https://hyun-git.github.io/feed.xml"
BLOG_HOST = "hyun-git.github.io"
START = "<!-- recent-writing:start -->"
END = "<!-- recent-writing:end -->"
NS = {"atom": "http://www.w3.org/2005/Atom"}

def normalize_url(value):
    parts = urlsplit(value.strip())
    if parts.scheme != "https" or parts.netloc.lower() != BLOG_HOST or not parts.path.startswith("/"):
        raise ValueError(f"Feed link is outside the blog host: {value!r}")
    path = re.sub(r"/{2,}", "/", parts.path)
    return urlunsplit(("https", BLOG_HOST, path, parts.query, parts.fragment))

def read_rows():
    request = Request(FEED_URL, headers={"User-Agent": "Hyun-git-profile-readme/1.0"})
    with urlopen(request, timeout=30) as response:
        feed = ET.fromstring(response.read())
    rows = []
    for entry in feed.findall("atom:entry", NS):
        node = entry.find("atom:title", NS)
        title = unescape("".join(node.itertext()).strip()) if node is not None else ""
        if not title:
            continue
        links = entry.findall("atom:link", NS)
        href = next((item.get("href") for item in links if item.get("href") and item.get("rel", "alternate") == "alternate"), None)
        date = entry.findtext("atom:published", namespaces=NS) or entry.findtext("atom:updated", namespaces=NS)
        if not href or not date:
            continue
        published = datetime.fromisoformat(date.replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        display_date = published.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y.%m.%d")
        safe_title = title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
        rows.append(f"- [{safe_title}](<{normalize_url(href)}>) · {display_date}")
        if len(rows) == 3:
            break
    if not rows:
        raise RuntimeError("The feed did not contain any usable recent posts.")
    return rows

def update_readme(rows):
    path = Path("README.md")
    content = path.read_text(encoding="utf-8")
    if content.count(START) != 1 or content.count(END) != 1:
        raise RuntimeError("README.md must contain exactly one recent-writing marker pair.")
    start = content.index(START) + len(START)
    end = content.index(END)
    if end < start:
        raise RuntimeError("Recent-writing markers are out of order.")
    updated = content[:start] + "\n" + "\n".join(rows) + "\n" + content[end:]
    if updated == content:
        return False
    path.write_text(updated, encoding="utf-8")
    return True

if __name__ == "__main__":
    changed = update_readme(read_rows())
    print("Recent writing updated from Atom feed." if changed else "Recent writing is already current.")
