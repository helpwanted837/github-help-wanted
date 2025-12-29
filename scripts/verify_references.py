#!/usr/bin/env python3
"""
联网校验所有页面的 References 链接，生成可追溯报告（JSON + Markdown）。

说明：
- 本脚本不做“搜索引擎检索”，而是对文章中已列出的 References 做在线可达性与跳转校验，
  用于避免“伪造来源/死链”。
- 只抓取页面 <title>（可选），不保存正文，避免版权与体量问题。
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import requests
import yaml


TZ_8 = timezone(timedelta(hours=8))
CONTENT_DIR = Path("content")


def _ensure_trailing_slash(url: str) -> str:
    if url == "/":
        return "/"
    return url if url.endswith("/") else f"{url}/"


def _url_to_path(url: str, page_type: str) -> Path:
    url = _ensure_trailing_slash(url)
    if url == "/":
        return CONTENT_DIR / "_index.md"

    parts = [p for p in url.strip("/").split("/") if p]
    if page_type == "trust":
        return CONTENT_DIR / "pages" / f"{parts[-1]}.md"
    if len(parts) == 1:
        return CONTENT_DIR / parts[0] / "_index.md"
    return CONTENT_DIR / parts[0] / f"{parts[1]}.md"


def _parse_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    _, fm, body = parts
    meta = yaml.safe_load(fm) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body.lstrip("\n")


REF_URL_RE = re.compile(r"\]\((https?://[^)]+)\)")


def _extract_reference_urls(body: str) -> List[str]:
    if "## References" not in body:
        return []
    after = body.split("## References", 1)[1]
    # stop at next H2
    after = re.split(r"\n##\s+", after)[0]
    urls = []
    for m in REF_URL_RE.finditer(after):
        urls.append(m.group(1))
    # de-dup while preserving order
    seen = set()
    out = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _safe_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def _read_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    if not m:
        return ""
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    # cap
    return title[:200]


@dataclass(frozen=True)
class CheckResult:
    url: str
    ok: bool
    status: int | None
    final_url: str | None
    title: str | None
    elapsed_ms: int
    error: str | None


def _check_url(session: requests.Session, url: str, *, timeout: float, fetch_title: bool) -> CheckResult:
    t0 = time.time()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; content-audit/1.0; +https://example.invalid)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def done(*, ok: bool, status: int | None, final_url: str | None, title: str | None, error: str | None) -> CheckResult:
        elapsed_ms = int(round((time.time() - t0) * 1000))
        return CheckResult(
            url=url,
            ok=ok,
            status=status,
            final_url=final_url,
            title=title,
            elapsed_ms=elapsed_ms,
            error=error,
        )

    try:
        # HEAD first (lighter); some sites block it → fallback to GET
        r = session.head(url, allow_redirects=True, timeout=timeout, headers=headers)
        status = int(r.status_code)
        final_url = str(r.url) if getattr(r, "url", None) else None

        if status >= 400 or (fetch_title and "text/html" in (r.headers.get("content-type") or "").lower()):
            # GET for better compatibility and to optionally parse title
            rg = session.get(url, allow_redirects=True, timeout=timeout, headers=headers)
            status = int(rg.status_code)
            final_url = str(rg.url) if getattr(rg, "url", None) else final_url
            title = _read_title(rg.text) if fetch_title and rg.text else None
            ok = 200 <= status < 400
            return done(ok=ok, status=status, final_url=final_url, title=title, error=None if ok else f"HTTP {status}")

        ok = 200 <= status < 400
        return done(ok=ok, status=status, final_url=final_url, title=None, error=None if ok else f"HTTP {status}")
    except Exception as e:
        return done(ok=False, status=None, final_url=None, title=None, error=str(e))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="data/content_plan_181.yaml")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--fetch-title", action="store_true", help="对 HTML 页面提取 <title>（会更慢）")
    parser.add_argument("--max-urls", type=int, default=0, help="仅校验前 N 个唯一 URL（0=全部）")
    args = parser.parse_args()

    plan = yaml.safe_load(Path(args.plan).read_text(encoding="utf-8"))
    pages = plan.get("pages") if isinstance(plan, dict) else None
    if not isinstance(pages, list):
        raise SystemExit(f"Invalid plan: {args.plan}")

    page_rows: List[Dict[str, Any]] = []
    all_urls: List[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        ptype = str(page.get("type") or "")
        url = str(page.get("url") or "")
        path = _url_to_path(url, ptype)
        raw = path.read_text(encoding="utf-8") if path.exists() else ""
        _, body = _parse_frontmatter(raw)
        refs = _extract_reference_urls(body)
        page_rows.append(
            {
                "url": url,
                "type": ptype,
                "path": str(path),
                "refs": refs,
            }
        )
        all_urls.extend(refs)

    # unique urls
    seen = set()
    unique_urls: List[str] = []
    for u in all_urls:
        if u in seen:
            continue
        seen.add(u)
        unique_urls.append(u)

    if args.max_urls and args.max_urls > 0:
        unique_urls = unique_urls[: args.max_urls]

    started_at = datetime.now(TZ_8).isoformat(timespec="seconds")
    results: Dict[str, Any] = {
        "started_at": started_at,
        "timeout_seconds": args.timeout,
        "fetch_title": bool(args.fetch_title),
        "unique_urls": len(unique_urls),
        "pages": page_rows,
        "checks": {},
    }

    session = requests.Session()
    ok_count = 0
    for i, u in enumerate(unique_urls, 1):
        cr = _check_url(session, u, timeout=args.timeout, fetch_title=bool(args.fetch_title))
        results["checks"][u] = {
            "ok": cr.ok,
            "status": cr.status,
            "final_url": cr.final_url,
            "title": cr.title,
            "elapsed_ms": cr.elapsed_ms,
            "error": cr.error,
            "domain": _safe_domain(u),
        }
        if cr.ok:
            ok_count += 1
        if i % 10 == 0:
            print(f"checked={i}/{len(unique_urls)} ok={ok_count}")

    finished_at = datetime.now(TZ_8).isoformat(timespec="seconds")
    results["finished_at"] = finished_at
    results["ok"] = ok_count
    results["failed"] = len(unique_urls) - ok_count

    out_dir = Path("research")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(TZ_8).strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"reference_checks_{stamp}.json"
    md_path = out_dir / f"reference_checks_{stamp}.md"

    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # markdown summary
    lines = [
        "# Reference Checks",
        "",
        f"- Started: {started_at}",
        f"- Finished: {finished_at}",
        f"- Unique URLs: {len(unique_urls)}",
        f"- OK: {ok_count}",
        f"- Failed: {len(unique_urls) - ok_count}",
        "",
        "## Failed URLs",
        "",
    ]
    failed_any = False
    for u in unique_urls:
        info = results["checks"].get(u) or {}
        if info.get("ok"):
            continue
        failed_any = True
        status = info.get("status")
        err = info.get("error") or ""
        lines.append(f"- {u} ({status or 'ERR'}) {err}")
    if not failed_any:
        lines.append("- (none)")

    lines += [
        "",
        "## Domains",
        "",
    ]
    domain_counts: Dict[str, int] = {}
    for u in unique_urls:
        d = _safe_domain(u)
        domain_counts[d] = domain_counts.get(d, 0) + 1
    for d, n in sorted(domain_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {d}: {n}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")

    return 0 if ok_count == len(unique_urls) else 1


if __name__ == "__main__":
    raise SystemExit(main())

