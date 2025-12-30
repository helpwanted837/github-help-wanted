#!/usr/bin/env python3
"""
内链覆盖率审计（基于 data/internal_links.json）

目标（对应 DEVELOPER_TASKS / 类别 F1）：
1) 统计每篇已发布文章的内链数量（出链/入链）
2) 识别孤立页面（无入链）
3) 输出可追溯的报告（含文件路径/URL/标题），便于后续补链

说明：
- github-help-wanted 的 internal_links.json 按 URL 组织：
  {
    "/open-source/": {
      "links": [{"url": "...", "title": "...", "score": 0.1234}, ...],
      "updated": "2025-12-30T..."
    }
  }
- “已发布”判定对齐 scripts/generate_internal_links.py：
  draft != true 且（date 缺省视为可发布；若有 date 则 date <= now(UTC)）
- 默认排除 content/pages/* 与站点根路径 "/"（避免把信任页/首页混入内容网络）

退出码：
- 默认 exit 0（仅输出报告）
- 开启 --fail 后：存在 missing_entries 或 orphans 时 exit 1
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


CONTENT_DIR = Path("content")
DEFAULT_INTERNAL_LINKS = Path("data/internal_links.json")


@dataclass(frozen=True)
class PageMeta:
    url: str
    title: str
    path: Path
    section: str
    published_at_utc: datetime | None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    _sep, fm, body = parts
    meta = yaml.safe_load(fm) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return None


def _parse_now_utc(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _ensure_trailing_slash(url: str) -> str:
    if url == "/":
        return "/"
    return url if url.endswith("/") else f"{url}/"


def _path_to_url(path: Path, meta: dict[str, Any]) -> str:
    if isinstance(meta.get("url"), str) and meta["url"].strip():
        return _ensure_trailing_slash(meta["url"].strip())

    rel = path.relative_to(CONTENT_DIR)
    parts = list(rel.parts)
    filename = parts[-1]

    if filename == "_index.md":
        if len(parts) == 1:
            return "/"
        return _ensure_trailing_slash("/" + "/".join(parts[:-1]) + "/")

    slug = Path(filename).stem
    return _ensure_trailing_slash("/" + "/".join(parts[:-1] + [slug]) + "/")


def _is_publishable(meta: dict[str, Any], now_utc: datetime) -> bool:
    if meta.get("draft") is True:
        return False
    dt = _parse_datetime(meta.get("date"))
    if dt is None:
        return True
    return dt <= now_utc


def _load_pages(*, now_utc: datetime) -> dict[str, PageMeta]:
    pages: dict[str, PageMeta] = {}

    for md_path in sorted(CONTENT_DIR.rglob("*.md")):
        raw = _read_text(md_path)
        meta, _body = _split_frontmatter(raw)

        url = _path_to_url(md_path, meta)
        section = md_path.relative_to(CONTENT_DIR).parts[0] if md_path != CONTENT_DIR / "_index.md" else ""

        if section == "pages":
            continue
        if url == "/":
            continue
        if not _is_publishable(meta, now_utc):
            continue

        title = str(meta.get("title") or "").strip() or url
        published_at_utc = _parse_datetime(meta.get("date"))

        pages[url] = PageMeta(
            url=url,
            title=title,
            path=md_path,
            section=section,
            published_at_utc=published_at_utc,
        )

    return pages


def _load_internal_links(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(_read_text(path))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def audit_internal_links(
    *,
    internal_links_path: Path,
    now_utc: datetime,
    fail: bool,
    max_report: int,
    json_out: Path | None,
) -> int:
    pages = _load_pages(now_utc=now_utc)
    eligible_urls = set(pages.keys())

    data = _load_internal_links(internal_links_path)

    missing_entries = sorted([url for url in eligible_urls if url not in data])

    out_unique: dict[str, set[str]] = {url: set() for url in eligible_urls}
    out_total: dict[str, int] = {url: 0 for url in eligible_urls}
    inbound_sources: dict[str, set[str]] = {url: set() for url in eligible_urls}

    for src_url, payload in data.items():
        if src_url not in eligible_urls:
            continue
        if not isinstance(payload, dict):
            continue
        links = payload.get("links")
        if not isinstance(links, list):
            continue

        for link in links:
            if not isinstance(link, dict):
                continue
            target = str(link.get("url") or "").strip()
            if not target:
                continue
            target = _ensure_trailing_slash(target)
            if target not in eligible_urls:
                continue

            out_total[src_url] += 1
            out_unique[src_url].add(target)
            inbound_sources[target].add(src_url)

    inbound_count = {url: len(srcs) for url, srcs in inbound_sources.items()}
    outbound_unique_count = {url: len(tgts) for url, tgts in out_unique.items()}

    orphans = sorted([url for url in eligible_urls if inbound_count.get(url, 0) == 0])

    total_pages = len(eligible_urls)
    avg_out = round(sum(outbound_unique_count.values()) / total_pages, 2) if total_pages else 0.0
    avg_in = round(sum(inbound_count.values()) / total_pages, 2) if total_pages else 0.0

    top_inbound = sorted(eligible_urls, key=lambda u: (-inbound_count.get(u, 0), u))[:10]
    top_outbound = sorted(eligible_urls, key=lambda u: (-outbound_unique_count.get(u, 0), u))[:10]

    print("internal_links_audit: github-help-wanted")
    print(f"- now_utc: {now_utc.isoformat().replace('+00:00', 'Z')}")
    print(f"- eligible_pages: {total_pages}")
    print(f"- missing_entries: {len(missing_entries)}")
    print(f"- orphans(inbound=0): {len(orphans)}")
    print(f"- avg_outbound_unique: {avg_out}")
    print(f"- avg_inbound_unique_sources: {avg_in}")

    def _print_url_list(title: str, urls: list[str]) -> None:
        if not urls:
            return
        print(f"\n{title}:")
        for url in urls[:max_report]:
            pm = pages.get(url)
            extra = f" | {pm.title}" if pm else ""
            path_str = str(pm.path) if pm else ""
            print(f"- {url}{extra} {path_str}".rstrip())
        if len(urls) > max_report:
            print(f"... (+{len(urls) - max_report} more)")

    _print_url_list("missing_entries（内容存在但 internal_links.json 缺失）", missing_entries)
    _print_url_list("orphans（无入链，建议优先补链）", orphans)

    print("\nTop inbound（入链最多）:")
    for url in top_inbound:
        pm = pages.get(url)
        title = pm.title if pm else url
        print(f"- {inbound_count.get(url, 0):>3} ← {url} | {title}")

    print("\nTop outbound（出链最多，unique targets）:")
    for url in top_outbound:
        pm = pages.get(url)
        title = pm.title if pm else url
        print(f"- {outbound_unique_count.get(url, 0):>3} → {url} | {title}")

    if json_out:
        payload = {
            "generated_at_utc": now_utc.isoformat().replace("+00:00", "Z"),
            "internal_links_path": str(internal_links_path),
            "summary": {
                "eligible_pages": total_pages,
                "missing_entries": len(missing_entries),
                "orphans": len(orphans),
                "avg_outbound_unique": avg_out,
                "avg_inbound_unique_sources": avg_in,
            },
            "issues": {
                "missing_entries": [
                    {
                        "url": u,
                        "title": pages[u].title if u in pages else "",
                        "path": str(pages[u].path) if u in pages else "",
                    }
                    for u in missing_entries
                ],
                "orphans": [
                    {
                        "url": u,
                        "title": pages[u].title if u in pages else "",
                        "path": str(pages[u].path) if u in pages else "",
                    }
                    for u in orphans
                ],
            },
            "pages": {
                url: {
                    "title": pages[url].title,
                    "path": str(pages[url].path),
                    "section": pages[url].section,
                    "published_at_utc": (
                        pages[url].published_at_utc.isoformat().replace("+00:00", "Z")
                        if pages[url].published_at_utc
                        else None
                    ),
                    "inbound_unique_sources": inbound_count.get(url, 0),
                    "outbound_unique_targets": outbound_unique_count.get(url, 0),
                    "outbound_total_links": out_total.get(url, 0),
                }
                for url in sorted(eligible_urls)
            },
        }
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nReport written: {json_out}")

    if not fail:
        return 0
    if missing_entries or orphans:
        print("\n::warning::internal_links_audit failed (missing_entries/orphans present)")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--internal-links", default=str(DEFAULT_INTERNAL_LINKS), help="内链数据文件（默认 data/internal_links.json）。")
    parser.add_argument("--now-utc", default="", help="指定 now(UTC)（ISO8601，例如 2025-12-30T12:00:00Z）。")
    parser.add_argument("--fail", action="store_true", help="严格模式：发现孤立页/缺失条目则返回非 0。")
    parser.add_argument("--max-report", type=int, default=50, help="最多输出多少条孤立页/缺失条目（默认 50）。")
    parser.add_argument("--json-out", default="", help="可选：写出 JSON 报告路径。")
    args = parser.parse_args()

    internal_links_path = Path(args.internal_links)
    now_utc = _parse_now_utc(args.now_utc or None)
    json_out = Path(args.json_out) if args.json_out.strip() else None

    if not internal_links_path.exists():
        print(f"::error::Missing internal links file: {internal_links_path}")
        return 2

    return audit_internal_links(
        internal_links_path=internal_links_path,
        now_utc=now_utc,
        fail=bool(args.fail),
        max_report=int(args.max_report),
        json_out=json_out,
    )


if __name__ == "__main__":
    raise SystemExit(main())

