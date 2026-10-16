#!/usr/bin/env python3
"""Fetch RSS/Atom feeds and filter recent research entries by topic keywords."""

from __future__ import annotations

import argparse
import email.utils
import html
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Iterable


ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"


@dataclass
class Entry:
    feed_url: str
    feed_title: str
    title: str
    link: str
    published: str
    published_iso: str | None
    authors: str
    summary: str
    matched_keywords: list[str]
    relevance_score: int


def strip_markup(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_date(value: str) -> datetime | None:
    if not value:
        return None

    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass

    candidates = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ]
    for fmt in candidates:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def child_text(node: ET.Element, names: Iterable[str]) -> str:
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def first_link(node: ET.Element) -> str:
    rss_link = child_text(node, ["link"])
    if rss_link:
        return rss_link
    for link in node.findall(f"{ATOM}link"):
        href = link.attrib.get("href")
        if href:
            return href
    return ""


def fetch(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 RSS Research Monitor "
                "(compatible; Codex skill; +https://openai.com)"
            ),
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def parse_feed(feed_url: str, raw: bytes) -> tuple[str, list[dict[str, str]]]:
    root = ET.fromstring(raw)
    channel = root.find("channel")
    if channel is not None:
        feed_title = child_text(channel, ["title"])
        items = []
        for item in channel.findall("item"):
            items.append(
                {
                    "title": child_text(item, ["title"]),
                    "link": first_link(item),
                    "published": child_text(item, ["pubDate", "date", f"{DC}date"]),
                    "authors": child_text(item, [f"{DC}creator", "author", "creator"]),
                    "summary": child_text(item, ["description", "summary", "content"]),
                }
            )
        return feed_title, items

    if root.tag == f"{ATOM}feed":
        feed_title = child_text(root, [f"{ATOM}title"])
        items = []
        for entry in root.findall(f"{ATOM}entry"):
            authors = []
            for author in entry.findall(f"{ATOM}author"):
                name = child_text(author, [f"{ATOM}name"])
                if name:
                    authors.append(name)
            items.append(
                {
                    "title": child_text(entry, [f"{ATOM}title"]),
                    "link": first_link(entry),
                    "published": child_text(entry, [f"{ATOM}published", f"{ATOM}updated"]),
                    "authors": ", ".join(authors),
                    "summary": child_text(entry, [f"{ATOM}summary", f"{ATOM}content"]),
                }
            )
        return feed_title, items

    raise ValueError(f"Unsupported feed format for {feed_url}")


def score_entry(title: str, summary: str, topic: str, keywords: list[str]) -> tuple[list[str], int]:
    haystack = f"{title} {summary}".lower()
    hits = []
    score = 0
    topic_words = [word for word in re.split(r"[^a-zA-Z0-9+-]+", topic.lower()) if word]

    for keyword in keywords:
        needle = keyword.strip().lower()
        if needle and needle in haystack:
            hits.append(keyword.strip())
            score += 3 if needle in title.lower() else 1

    for word in topic_words:
        if len(word) >= 4 and word in haystack and word not in [h.lower() for h in hits]:
            hits.append(word)
            score += 2 if word in title.lower() else 1

    bio_terms = ["enzyme", "enzymatic", "protein", "active site", "substrate", "whole-cell"]
    catalysis_terms = ["catalysis", "catalyst", "reaction", "transformation", "biosynthesis"]
    if any(term in haystack for term in bio_terms) and any(term in haystack for term in catalysis_terms):
        score += 4

    return sorted(set(hits), key=str.lower), score


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", action="append", required=True, help="RSS/Atom feed URL. Repeat for multiple feeds.")
    parser.add_argument("--topic", required=True, help="Research topic, e.g. biocatalysis.")
    parser.add_argument("--keywords", default="", help="Comma-separated topic keywords.")
    parser.add_argument("--hours", type=float, default=24.0, help="Lookback window in hours.")
    parser.add_argument("--now", default="", help="Override current UTC time as ISO timestamp for testing.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    now = parse_date(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        print(json.dumps({"error": f"Could not parse --now: {args.now}"}, ensure_ascii=False), file=sys.stderr)
        return 2

    window_start = now - timedelta(hours=args.hours)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    all_entries: list[Entry] = []
    errors = []
    total_entries = 0
    recent_entries = 0

    for feed_url in args.feed:
        try:
            feed_title, raw_items = parse_feed(feed_url, fetch(feed_url, args.timeout))
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            errors.append({"feed_url": feed_url, "error": str(exc)})
            continue

        total_entries += len(raw_items)
        for item in raw_items:
            published_dt = parse_date(item["published"])
            if published_dt is None or published_dt < window_start or published_dt > now:
                continue
            recent_entries += 1
            title = strip_markup(item["title"])
            summary = strip_markup(item["summary"])
            hits, score = score_entry(title, summary, args.topic, keywords)
            if score <= 0:
                continue
            all_entries.append(
                Entry(
                    feed_url=feed_url,
                    feed_title=feed_title,
                    title=title,
                    link=item["link"],
                    published=item["published"],
                    published_iso=published_dt.isoformat(),
                    authors=strip_markup(item["authors"]),
                    summary=summary,
                    matched_keywords=hits,
                    relevance_score=score,
                )
            )

    all_entries.sort(key=lambda entry: (entry.relevance_score, entry.published_iso or ""), reverse=True)
    result = {
        "topic": args.topic,
        "window_hours": args.hours,
        "window_start_utc": window_start.isoformat(),
        "window_end_utc": now.isoformat(),
        "feeds_checked": args.feed,
        "total_entries_seen": total_entries,
        "recent_entries_seen": recent_entries,
        "matched_entries": [asdict(entry) for entry in all_entries],
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
