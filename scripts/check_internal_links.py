#!/usr/bin/env python3
"""
检查 Hugo 构建产物（默认 public/）中的站内链接是否存在。

目标：
- 尽早发现“排期发布”导致的内部死链（例如链接到尚未发布的页面）。
- 避免网络请求：把 root-relative URL 和站点绝对 URL 映射到 public/ 下的文件路径。

说明：
- 有意跳过相对链接（不以 "/" 开头），避免复杂的相对路径解析。
- 默认仅输出 GitHub Actions warning，不会让构建失败；需要严格模式时加 --fail。
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urlparse


INTERNAL_HOSTS = {"github-help-wanted.com", "www.github-help-wanted.com"}
HREF_RE = re.compile(r"""href\s*=\s*(?P<q>["'])(?P<u>.*?)(?P=q)""", re.IGNORECASE)


def _normalize_internal_target(url: str) -> str | None:
    url = (url or "").strip()
    if not url:
        return None

    # Drop fragment and query.
    url, _frag = urldefrag(url)
    if "?" in url:
        url = url.split("?", 1)[0]
    url = url.strip()
    if not url:
        return None

    lowered = url.lower()
    if lowered.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None

    # Protocol-relative.
    if url.startswith("//"):
        url = "https:" + url

    # Absolute URLs: only treat our domain as internal.
    if lowered.startswith(("http://", "https://")):
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if host not in INTERNAL_HOSTS:
            return None
        url = parsed.path or "/"

    # Only handle root-relative URLs.
    if not url.startswith("/"):
        return None

    # Normalize.
    while "//" in url:
        url = url.replace("//", "/")

    if url == "/":
        return "index.html"

    rel = url.lstrip("/")
    rel_path = Path(rel)

    # Explicit file.
    if rel_path.suffix:
        return rel

    # Pretty URL.
    if url.endswith("/"):
        return str(rel_path / "index.html")
    return str(rel_path / "index.html")


def _iter_html_files(public_dir: Path) -> list[Path]:
    return [p for p in public_dir.rglob("*.html") if p.is_file()]


def _write_report_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_internal_links(*, public_dir: Path, fail: bool, max_report: int, report_json: Path | None) -> int:
    missing_targets: dict[str, set[str]] = {}

    html_files = _iter_html_files(public_dir)
    for html_path in html_files:
        try:
            text = html_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = html_path.read_text(encoding="utf-8", errors="replace")

        for match in HREF_RE.finditer(text):
            href = match.group("u").strip()
            target = _normalize_internal_target(href)
            if not target:
                continue

            target_path = public_dir / target
            if target_path.exists():
                continue

            src = str(html_path.relative_to(public_dir))
            missing_targets.setdefault(target, set()).add(src)

    if not missing_targets:
        print("internal_link_check: OK (0 broken)")
        if report_json:
            _write_report_json(
                report_json,
                {
                    "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "public_dir": str(public_dir),
                    "broken_targets": 0,
                    "broken_references": 0,
                    "targets": [],
                },
            )
        return 0

    broken_refs = sum(len(sources) for sources in missing_targets.values())
    print(f"::warning::Found {broken_refs} broken internal link references")

    shown = 0
    for target, sources in sorted(missing_targets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(f"- {target} (referenced by {len(sources)} pages)")
        for src in sorted(sources)[:3]:
            print(f"  - {src}")
        shown += len(sources)
        if shown >= max_report:
            remaining = broken_refs - shown
            if remaining > 0:
                print(f"... (+{remaining} more references)")
            break

    if report_json:
        targets = [
            {"target": target, "sources": sorted(sources)}
            for target, sources in sorted(missing_targets.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        ]
        _write_report_json(
            report_json,
            {
                "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "public_dir": str(public_dir),
                "broken_targets": len(missing_targets),
                "broken_references": broken_refs,
                "targets": targets,
            },
        )

    return 1 if fail else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", default="public", help="Hugo 输出目录（默认 public/）。")
    parser.add_argument("--fail", action="store_true", help="发现死链时返回非 0。")
    parser.add_argument(
        "--max-report",
        type=int,
        default=60,
        help="最多输出多少条死链引用（默认 60）。",
    )
    parser.add_argument(
        "--report-json",
        default="",
        help="可选：输出 JSON 报告路径（例如 .cache/internal_links/broken_report.json）。",
    )
    args = parser.parse_args()

    public_dir = Path(args.public)
    if not public_dir.exists():
        print(f"::error::Missing public dir: {public_dir}")
        return 2

    report_json = Path(args.report_json) if str(args.report_json).strip() else None
    return check_internal_links(public_dir=public_dir, fail=args.fail, max_report=args.max_report, report_json=report_json)


if __name__ == "__main__":
    raise SystemExit(main())
