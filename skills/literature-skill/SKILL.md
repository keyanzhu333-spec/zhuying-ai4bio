---
name: literature-skill
display_name: 文献 RSS 跟踪
display_name_en: Literature RSS Monitoring
description: Monitor one or more RSS/Atom feeds for recent research papers and summarize topic-specific progress. Use when the user provides RSS feed URLs, journal feeds, DOI feeds, arXiv feeds, or asks for recurring/daily research updates filtered by a theme such as biocatalysis, enzymes, catalysis, batteries, polymers, or any custom research topic.
description_zh: 监控一个或多个 RSS/Atom 文献源，按主题（如生物催化、酶、催化、电池、聚合物等）汇总最新研究进展。适用于文献订阅、期刊/DOI/arXiv 源跟踪与每日研究快报。
description_en: Monitor one or more RSS/Atom feeds for recent research papers and summarize topic-specific progress. Use for journal, DOI, or arXiv feed tracking and recurring daily research updates filtered by a custom theme.
category: 科研/生物
version: 1.0.0
author: 小猪莹(keyanzhu999)
---

# Literature Skill

Use this skill to turn RSS/Atom feeds into short research updates for a user-defined topic and recent time window.

## Workflow

1. Collect the feed URLs, topic, keywords, and time window. Default to the last 24 hours when the user asks for daily updates.
2. Run `scripts/rss_research_monitor.py` to fetch and normalize feed entries.
3. If a feed returns 403, Cloudflare, or browser-only content, open the feed in the browser and extract the visible XML `<item>`/`<entry>` nodes instead of forcing command-line fetches.
4. Use the script or browser-extracted entries as the first-pass candidate set.
5. Apply a final semantic review: keep entries that are genuinely related to the topic, not just incidental keyword hits. Review every configured source separately before deduplicating; do not rely only on a manually selected shortlist.
6. Produce two clearly separated editions when the user requests a push: (a) **重点推荐版**, containing the strongest and most actionable matches; then (b) **全部相关版**, containing every semantically relevant match that survives review, with no arbitrary item limit. Never describe the重点推荐版 as the complete result.
7. Reply in the user's preferred language. For Chinese users, include both a faithful Chinese title translation and the original English title, then date, DOI/link, authors when available, and a one-sentence relevance note.

## Quick Start

Run from any working directory:

```bash
python3 ~/.codex/skills/literature-skill/scripts/rss_research_monitor.py \
  --feed "https://pubs.acs.org/action/showFeed?type=axatoc&feed=rss&jc=achre4" \
  --topic "biocatalysis" \
  --keywords "biocatalysis,biocatalyst,enzyme,enzymatic,biosynthesis,biotransformation,whole-cell catalysis,directed evolution,protein engineering,oxidase,reductase,dehydrogenase,hydrolase,transferase,lyase,ligase,isomerase" \
  --hours 24
```

For multiple feeds, repeat `--feed`.

If the JSON output has `errors` for a feed but the same URL opens in the user's browser, use the browser page as the source of truth. ACS feeds may block non-browser requests while still rendering RSS XML in the in-app browser.

## Output Guidance

When matches exist, group the response as:

- `重点推荐版`: list the strongest matches first and label this as a curated subset.
- `全部相关版`: list every semantically relevant entry found across all feeds; retain high recall and do not cap at 20 items.
- `中文标题` and `English title`: always show both. Translate the title faithfully; do not replace or omit the original English title.
- `为什么相关`: one short sentence for each entry, based on title/summary/keywords.
- `来源`: include the feed journal/source if available and DOI/link.

When no matches exist, say so clearly and include:

- How many recent entries were checked.
- The exact time window.
- Any near-miss entries if they may interest the user.

## Relevance Rules

Use a two-pass policy: high precision for the重点推荐版, high recall for the全部相关版. The complete edition must not be shortened merely for convenience.

Treat as strong matches:

- Topic phrase in title, summary, DOI metadata, or keywords.
- Enzyme/protein terms plus a catalysis, transformation, reaction, mechanism, active-site, or substrate term.
- Whole-cell catalysis, biosynthesis, metabolic engineering, directed evolution, enzyme engineering, or biotransformation.
- Synthetic biology terms such as genetic circuits, pathway engineering, heterologous expression, chassis organisms, cell-free systems, genome engineering, CRISPR, biosensors, microbial cell factories, or biomanufacturing when they are part of the user's topic.
- Protein design/modeling terms such as de novo design, computational protein design, protein folding, structure prediction, protein language model, protein diffusion model, inverse folding, AlphaFold, ESMFold, RFdiffusion, Rosetta, docking, or binding free energy when the user includes protein design/model topics.

Treat as weak or near-miss:

- General catalysis without biological catalysts.
- General protein/biomolecule papers without design, modeling, folding, structure prediction, binding, reaction, or catalytic context.
- Biomedical small-molecule papers unless they discuss enzymes or biocatalytic transformations.

Before finalizing the全部相关版, run a source-by-source completeness check against the configured feed list. Record the number of entries checked and retain borderline papers when they plausibly fit the user's declared themes; remove only clearly unrelated items and duplicates.

## Automation Use

For daily monitoring, create a Codex automation whose prompt includes:

- Feed URLs.
- Topic and keyword list.
- Time window: last 24 hours.
- Desired language and format.

For this user's daily research monitoring, default the schedule to every day at 06:00 Beijing time unless the user asks for another time.

The automation prompt should ask Codex to use this skill and report only when there are relevant updates unless the user asks for a daily "no results" note.

For Chinese briefings, each matched paper must include:

- Chinese title: a concise, faithful translation.
- English title: the original title from the feed/metadata.
- Category labels, source feed, publication date/time, authors when available, DOI/link, and relevance note.
