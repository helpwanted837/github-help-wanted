#!/usr/bin/env python3
"""
离线 SEO 审计（不访问网络）：

1) <meta name="description"> 是否存在 + 长度是否合理
2) Open Graph: og:image 是否存在 + 若为站内路径则检查文件是否存在
3) JSON-LD（application/ld+json）是否为合法 JSON

说明：
- 使用 HTMLParser 解析（兼容 Hugo --minify 后的无引号属性）
- 默认跳过 Pagefind bundle

用法：
  python scripts/audit_seo.py --public public
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class Finding:
    level: str  # "error" | "warn"
    path: Path
    message: str


class _SeoHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta_description: Optional[str] = None
        self.og_image: Optional[str] = None
        self.og_type: Optional[str] = None
        self.jsonld_blocks: list[str] = []
        self._in_jsonld = False
        self._jsonld_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag.lower() == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")
            if name == "description" and content and self.meta_description is None:
                self.meta_description = content.strip()
            if prop == "og:image" and content and self.og_image is None:
                self.og_image = content.strip()
            if prop == "og:type" and content and self.og_type is None:
                self.og_type = content.strip()

        if tag.lower() == "script":
            t = attrs_dict.get("type", "").lower()
            if t == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_jsonld:
            self._in_jsonld = False
            raw = "".join(self._jsonld_buf).strip()
            if raw:
                self.jsonld_blocks.append(raw)
            self._jsonld_buf = []

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._jsonld_buf.append(data)


def _iter_html_files(public_dir: Path) -> Iterable[Path]:
    for p in public_dir.rglob("*.html"):
        if "pagefind" in p.parts:
            continue
        yield p


def _check_local_asset_exists(public_dir: Path, url: str) -> bool:
    if not url:
        return True
    parsed = urlparse(url)
    path = parsed.path
    if not path:
        return True
    if not path.startswith("/"):
        candidate = public_dir / path
    else:
        candidate = public_dir / path.lstrip("/")
    return candidate.exists()


def _collect_schema_types(obj: Any) -> set[str]:
    types: set[str] = set()

    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, str) and t.strip():
            types.add(t.strip().lower())
        elif isinstance(t, list):
            for v in t:
                if isinstance(v, str) and v.strip():
                    types.add(v.strip().lower())

        for v in obj.values():
            types |= _collect_schema_types(v)
        return types

    if isinstance(obj, list):
        for it in obj:
            types |= _collect_schema_types(it)
        return types

    return types


def main() -> int:
    parser = argparse.ArgumentParser(description="离线 SEO 审计（meta/og/jsonld）")
    parser.add_argument("--public", type=Path, default=Path("public"))
    parser.add_argument("--min-desc", type=int, default=150)
    parser.add_argument("--max-desc", type=int, default=160)
    parser.add_argument(
        "--duplicates-as-error",
        action="store_true",
        help="将重复 meta description 视为 error（默认仅 warn）",
    )
    args = parser.parse_args()

    findings: list[Finding] = []
    file_count = 0
    desc_to_files: dict[str, list[Path]] = defaultdict(list)

    for html_file in _iter_html_files(args.public):
        text = html_file.read_text(encoding="utf-8", errors="ignore")

        # Hugo aliases（例如 /p/1/）会生成 meta refresh 的“跳转页”，不属于需要审计的内容页
        if "http-equiv=refresh" in text.lower():
            continue

        file_count += 1

        p = _SeoHtmlParser()
        p.feed(text)

        desc = (p.meta_description or "").strip()
        if not desc:
            findings.append(Finding("error", html_file, '缺少 <meta name="description">'))
        else:
            desc_to_files[desc].append(html_file)
            n = len(desc)
            if n < args.min_desc:
                findings.append(Finding("warn", html_file, f"description 过短：{n} chars"))
            if n > args.max_desc:
                findings.append(Finding("warn", html_file, f"description 过长：{n} chars"))

        og = (p.og_image or "").strip()
        if not og:
            findings.append(Finding("error", html_file, "缺少 og:image"))
        else:
            if og.startswith(("/", "http://", "https://")):
                if not _check_local_asset_exists(args.public, og):
                    findings.append(Finding("error", html_file, f"og:image 目标文件不存在：{og}"))

        jsonld_objs: list[Any] = []
        for block in p.jsonld_blocks:
            try:
                jsonld_objs.append(json.loads(block))
            except Exception as exc:
                msg = str(exc).splitlines()[0]
                findings.append(Finding("error", html_file, f"JSON-LD 解析失败：{msg}"))

        schema_types = set()
        for obj in jsonld_objs:
            schema_types |= _collect_schema_types(obj)

        og_type = (p.og_type or "").strip().lower()
        if og_type == "article":
            if not ({"article", "blogposting", "newsarticle"} & schema_types):
                findings.append(Finding("warn", html_file, "og:type=article 但未检测到 Article/BlogPosting/NewsArticle schema"))
        elif og_type == "website":
            if "website" not in schema_types:
                findings.append(Finding("warn", html_file, "og:type=website 但未检测到 WebSite schema"))

    dup_level = "error" if args.duplicates_as_error else "warn"
    for desc, files in desc_to_files.items():
        if len(files) <= 1:
            continue
        files = [p for p in files if p.name != "404.html"]
        if len(files) <= 1:
            continue
        first = files[0]
        for f in files[1:]:
            findings.append(Finding(dup_level, f, f"meta description 重复（与 {first} 相同）"))

    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warn"]

    for f in errors + warns:
        print(f"[{f.level.upper()}] {f.path}: {f.message}")

    print(f"SEO audit: files={file_count} errors={len(errors)} warns={len(warns)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
