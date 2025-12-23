#!/usr/bin/env python3
"""
从 `docs/04-关键词清单.md` 的表格中生成 Hugo 内容页（占位稿）。

用途：
1) 按优先级批量生成 URL 对应的 content 文件
2) 统一 frontmatter（title/description/keywords/pillar/priority 等）

默认策略：
- 只处理带 P0/P1/P2 优先级的行（避免误解析 affiliate/其它表格）
- 默认生成 draft=true，避免薄内容直接上线
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


CONTENT_DIR = Path("content")


PRIORITY_RE = re.compile(r"\bP[0-2]\b")
URL_RE = re.compile(r"(/[^\s|]+/)")


@dataclass(frozen=True)
class KeywordRow:
    keyword: str
    url: str
    priority: str


def parse_rows(md: str) -> List[KeywordRow]:
    rows: List[KeywordRow] = []
    for line in md.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        if "URL" not in s and "/ " not in s and "/" not in s:
            continue

        priority_match = PRIORITY_RE.search(s)
        url_match = URL_RE.search(s)
        if not priority_match or not url_match:
            continue

        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) < 3:
            continue

        keyword = cols[1] if cols[0].isdigit() else cols[0]
        keyword = keyword.strip()

        rows.append(
            KeywordRow(
                keyword=keyword,
                url=url_match.group(1),
                priority=priority_match.group(0),
            )
        )
    return rows


def url_to_content_path(url: str) -> Tuple[Path, str]:
    clean = url.strip()
    if not (clean.startswith("/") and clean.endswith("/")):
        raise ValueError(f"非法 URL：{url}")
    parts = [p for p in clean.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"URL 不能映射为内容页（可能是 section）：{url}")
    section, slug = parts[0], parts[1]
    return CONTENT_DIR / section / f"{slug}.md", f"/{section}/"


def keyword_to_title(keyword: str) -> str:
    k = keyword.strip()
    if not k:
        return "Untitled"
    specials = {
        "github": "GitHub",
        "devops": "DevOps",
        "sdlc": "SDLC",
        "api": "API",
        "tdd": "TDD",
        "ssl": "SSL",
        "og": "OG",
        "seo": "SEO",
        "javascript": "JavaScript",
    }

    # 简单 Title Case：保留缩写与常见品牌写法
    words = []
    for w in re.split(r"\s+", k):
        key = w.strip().lower()
        if key in specials:
            words.append(specials[key])
        elif w.isupper() and len(w) <= 5:
            words.append(w)
        else:
            words.append(w.capitalize())
    return " ".join(words)


def write_page(
    path: Path,
    *,
    title: str,
    description: str,
    date: datetime,
    draft: bool,
    keyword: str,
    pillar: str,
    priority: str,
    overwrite: bool,
) -> bool:
    if path.exists() and not overwrite:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    iso = date.astimezone(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

    content = f"""---
title: "{title}"
description: "{description}"
date: {iso}
draft: {"true" if draft else "false"}

keywords: ["{keyword}"]
pillar: "{pillar}"
priority: "{priority}"
commercial_value: 3
affiliate_products: []
---

## Quick Answer

## Step-by-Step

## Common Mistakes

## FAQs
"""

    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="docs/04-关键词清单.md")
    parser.add_argument("--priority", choices=["P0", "P1", "P2", "ALL"], default="P0")
    parser.add_argument("--draft", choices=["true", "false"], default="true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--schedule-start", default="")
    parser.add_argument("--interval-minutes", type=int, default=90)
    args = parser.parse_args()

    md_path = Path(args.input)
    md = md_path.read_text(encoding="utf-8")
    rows = parse_rows(md)

    if args.priority != "ALL":
        rows = [r for r in rows if r.priority == args.priority]

    draft = args.draft == "true"

    start = None
    if args.schedule_start:
        start = datetime.fromisoformat(args.schedule_start.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    current = start or now

    created = 0
    for row in rows:
        try:
            out_path, pillar = url_to_content_path(row.url)
        except ValueError:
            continue

        title = keyword_to_title(row.keyword)
        description = f"Guide for: {row.keyword}"
        if write_page(
            out_path,
            title=title,
            description=description,
            date=current,
            draft=draft,
            keyword=row.keyword,
            pillar=pillar,
            priority=row.priority,
            overwrite=args.overwrite,
        ):
            created += 1
            current = current + timedelta(minutes=max(10, args.interval_minutes))

    print(f"generated={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
