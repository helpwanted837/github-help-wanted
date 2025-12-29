#!/usr/bin/env python3
"""
为 github-help-wanted 批量设置文章发布排期（2 篇/天，+08:00，时间随机）。

默认行为：
- 只处理 `content/` 下 `draft: true` 的 Markdown
- 排除 `content/pages/`（信任页/独立页通常应立即发布）
- 排除 `content/github-pages/template.md`（模板文件保留 draft）

输出：
- 直接改写 Markdown frontmatter 中的 `date:` 与 `draft:` 字段（尽量保持原有格式）
"""

from __future__ import annotations

import argparse
import random
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


SITE_TZ = timezone(timedelta(hours=8))
DATE_LINE_RE = re.compile(r"(?m)^date:\s*(.+?)\s*$")
DRAFT_LINE_RE = re.compile(r"(?m)^draft:\s*(.+?)\s*$")

CONTENT_DIR = Path("content")
EXCLUDE_REL_PATHS = {
    "github-pages/template.md",
}


@dataclass(frozen=True)
class Candidate:
    path: Path
    rel_path: str
    meta: dict[str, Any]


def _read_frontmatter(markdown_path: Path) -> dict[str, Any]:
    raw = markdown_path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = parts[1]
    data = yaml.safe_load(fm) or {}
    return data if isinstance(data, dict) else {}


def _pick_slot_time(rng: random.Random, slot: int) -> tuple[int, int, int]:
    # slot 0 = 早/中午（08:00-14:59），slot 1 = 下午/晚间（15:00-23:59）
    if slot == 0:
        hour = rng.choice([8, 9, 10, 11, 12, 13, 14])
    else:
        hour = rng.choice([15, 16, 17, 18, 19, 20, 21, 22, 23])
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)
    return hour, minute, second


def _priority_rank(meta: dict[str, Any]) -> int:
    raw = str(meta.get("priority") or "").strip().upper()
    if raw.startswith("P") and raw[1:].isdigit():
        return int(raw[1:])
    return 99


def _type_rank(meta: dict[str, Any]) -> int:
    t = str(meta.get("type") or "").strip().lower()
    order = {
        "pillar": 0,
        "trust": 1,
        "cluster": 2,
        "extension": 3,
    }
    return order.get(t, 50)


def _commercial_rank(meta: dict[str, Any]) -> int:
    try:
        return int(meta.get("commercial_value") or 0)
    except Exception:
        return 0


def _sort_key(c: Candidate) -> tuple[int, int, int, str]:
    # priority 越小越靠前；commercial_value 越大越靠前
    return (_priority_rank(c.meta), _type_rank(c.meta), -_commercial_rank(c.meta), c.rel_path)


def _replace_frontmatter_fields(markdown_path: Path, *, new_dt: datetime, new_draft: bool) -> None:
    text = markdown_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"Missing frontmatter: {markdown_path}")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid frontmatter delimiters: {markdown_path}")

    fm, body = parts[1], parts[2]

    date_match = DATE_LINE_RE.search(fm)
    if not date_match:
        raise ValueError(f"Missing date: {markdown_path}")

    # Preserve the original quoting style for date (single/double/none).
    existing = date_match.group(1).strip()
    quote = ""
    if (existing.startswith("'") and existing.endswith("'")) or (existing.startswith('"') and existing.endswith('"')):
        quote = existing[:1]
    date_replacement = f"date: {quote}{new_dt.isoformat()}{quote}"
    fm_new = DATE_LINE_RE.sub(date_replacement, fm, count=1)

    draft_match = DRAFT_LINE_RE.search(fm_new)
    if not draft_match:
        raise ValueError(f"Missing draft: {markdown_path}")
    draft_replacement = f"draft: {'true' if new_draft else 'false'}"
    fm_new = DRAFT_LINE_RE.sub(draft_replacement, fm_new, count=1)

    out = f"---\n{fm_new.strip()}\n---\n{body.lstrip()}"
    markdown_path.write_text(out, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20251229, help="随机种子（用于生成发布时间）。")
    parser.add_argument("--posts-per-day", type=int, default=2, help="每天发布篇数（默认 2）。")
    parser.add_argument(
        "--start-date",
        type=str,
        default="",
        help="开始日期（YYYY-MM-DD，+08:00）。默认：明天。",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="重排所有文章（忽略 draft 状态）。默认只处理 draft: true。",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入文件。")
    args = parser.parse_args()

    if args.posts_per_day <= 0:
        raise SystemExit("--posts-per-day 必须 > 0")

    start = (datetime.now(SITE_TZ).date() + timedelta(days=1))
    if args.start_date:
        start = date.fromisoformat(args.start_date)

    rng = random.Random(args.seed)

    candidates: list[Candidate] = []
    for md in sorted(CONTENT_DIR.rglob("*.md")):
        rel = md.relative_to(CONTENT_DIR)
        rel_str = rel.as_posix()
        if rel.parts and rel.parts[0] == "pages":
            continue
        if md.name == "_index.md":
            continue
        if rel_str in EXCLUDE_REL_PATHS:
            continue
        meta = _read_frontmatter(md)
        if args.all or meta.get("draft") is True:
            candidates.append(Candidate(path=md, rel_path=rel_str, meta=meta))

    candidates_sorted = sorted(candidates, key=_sort_key)

    changed = 0
    scheduled: list[tuple[str, datetime]] = []
    for i, c in enumerate(candidates_sorted):
        day_offset = i // args.posts_per_day
        slot = i % args.posts_per_day
        publish_day = start + timedelta(days=day_offset)
        hour, minute, second = _pick_slot_time(rng, slot)
        publish_dt = datetime(
            publish_day.year,
            publish_day.month,
            publish_day.day,
            hour,
            minute,
            second,
            tzinfo=SITE_TZ,
        )

        if args.dry_run:
            scheduled.append((c.rel_path, publish_dt))
            continue

        _replace_frontmatter_fields(c.path, new_dt=publish_dt, new_draft=False)
        scheduled.append((c.rel_path, publish_dt))
        changed += 1

    if scheduled:
        times = [dt for _, dt in scheduled]
        print(f"排期完成：{changed}/{len(scheduled)}")
        print(f"范围：{min(times).isoformat()} -> {max(times).isoformat()}")
        print(f"每天 {args.posts_per_day} 篇，起始日：{start.isoformat()}（+08:00）")
    else:
        print("未找到需要排期的文章（draft: true）。")

    if args.dry_run and scheduled:
        print("\n预览（前 20 条）：")
        for rel_path, dt in scheduled[:20]:
            print(f"- {rel_path}: {dt.isoformat()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
