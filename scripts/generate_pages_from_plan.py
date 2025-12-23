#!/usr/bin/env python3
"""
从 `data/content_plan_181.yaml` 生成 Hugo 内容页骨架（大纲稿）。

设计目标：
1) 统一骨架：Key Takeaways / 表格 / 引用 / References / FAQ(frontmatter)
2) 对已存在文件：默认“安全同步”（补齐 frontmatter & 缺失区块），不粗暴覆盖正文
3) 支持定时发布：新文件默认写入未来 date（+08:00），避免误上线
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

import yaml


CONTENT_DIR = Path("content")


SPECIAL_TITLE_CASE = {
    "github": "GitHub",
    "devops": "DevOps",
    "sdlc": "SDLC",
    "api": "API",
    "tdd": "TDD",
    "ssl": "SSL",
    "https": "HTTPS",
    "seo": "SEO",
    "ci/cd": "CI/CD",
    "ci": "CI",
    "cd": "CD",
    "javascript": "JavaScript",
    "golang": "Go",
    "gcp": "GCP",
    "aws": "AWS",
    "azure": "Azure",
    "okr": "OKR",
    "okrs": "OKRs",
    "prd": "PRD",
    "ux": "UX",
    "e2e": "E2E",
    "c#": "C#",
    "xunit": "xUnit",
    "nunit": "NUnit",
    "junit": "JUnit",
    "pytest": "pytest",
    "jest": "Jest",
    "mocha": "Mocha",
}


def _ensure_trailing_slash(url: str) -> str:
    if url == "/":
        return "/"
    return url if url.endswith("/") else f"{url}/"


def _parse_frontmatter(raw: str) -> Tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    _, fm, body = parts
    meta = yaml.safe_load(fm) or {}
    return meta, body.lstrip("\n")


def _dump_frontmatter(meta: dict) -> str:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm}\n---\n\n"


def _to_title_case(keyword: str) -> str:
    words: List[str] = []
    for w in re.split(r"\s+", keyword.strip()):
        if not w:
            continue
        key = w.strip().lower()
        if key in SPECIAL_TITLE_CASE:
            words.append(SPECIAL_TITLE_CASE[key])
        elif w.isupper() and len(w) <= 6:
            words.append(w)
        else:
            words.append(w.capitalize())
    return " ".join(words) if words else "Untitled"


def _guess_title(page_type: str, keyword: str) -> str:
    base = _to_title_case(keyword) if keyword else ""
    if page_type == "home":
        return "GitHub Help Wanted"
    if page_type == "trust":
        return base or "Page"
    if page_type == "pillar":
        return base or "Guide"
    if page_type in {"cluster", "extension"}:
        if "2025" in keyword:
            return base or "Guide"
        if any(s in keyword.lower() for s in ["hacktoberfest", "salary", "summer of code", "gsoc"]):
            return f"{base} (2025)" if base else "Guide (2025)"
        return base or "Guide"
    return base or "Guide"


def _guess_description(page_type: str, keyword: str) -> str:
    k = keyword.strip()
    if page_type == "home":
        return "Developer resources for open source, DevOps, SDLC, unit testing, and product management."
    if page_type == "trust":
        return ""
    if not k:
        return "Practical guide with examples, FAQs, and references."
    if page_type == "pillar":
        return f"Complete guide to {k}: definitions, best practices, tools, FAQs, and references."
    if page_type == "cluster":
        return f"Practical guide to {k} with steps, examples, FAQs, and authoritative references."
    return f"Deep dive into {k} with templates, checklists, FAQs, and references."


def _infer_section(url: str) -> str:
    if url == "/":
        return ""
    return url.strip("/").split("/")[0]


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


def _is_placeholder(body: str) -> bool:
    t = body.strip()
    if not t:
        return True
    if len(t) < 240 and t.count("\n") <= 6:
        return True
    markers = ["## Quick Answer", "## Step-by-Step", "## Common Mistakes", "## FAQs"]
    if all(m in t for m in markers) and len(t) < 900:
        return True
    return False


def _faq_block(keyword: str, count: int) -> List[dict]:
    topic = _to_title_case(keyword) if keyword else "this topic"
    qs = [
        f"What is {topic}?",
        f"Why does {topic} matter?",
        f"How do I get started with {topic}?",
        f"What are common mistakes with {topic}?",
        f"What tools are best for {topic}?",
        f"How long does it take to learn {topic}?",
        f"What are alternatives to {topic}?",
        f"How much does {topic} cost?",
    ]
    out: List[dict] = []
    for q in qs[: max(3, count)]:
        out.append(
            {
                "question": q,
                "answer": "Placeholder answer. Replace with a direct, data-backed answer and cite authoritative sources.",
            }
        )
    return out[:count]


def _howto_block(title: str) -> dict:
    return {
        "name": title if title.lower().startswith("how to") else f"How to {title}",
        "totalTime": "PT30M",
        "steps": [
            {"name": "Prepare prerequisites", "text": "List required accounts, tools, and access."},
            {"name": "Follow the core steps", "text": "Provide a clear, ordered checklist that works end-to-end."},
            {"name": "Verify and troubleshoot", "text": "Add validation steps and common fixes for errors."},
        ],
    }


def _comparison_table_block(title: str) -> dict:
    return {
        "name": f"{title} Comparison",
        "headers": ["Option", "Best for", "Pros", "Cons"],
        "rows": [
            ["Option A", "…", "…", "…"],
            ["Option B", "…", "…", "…"],
            ["Option C", "…", "…", "…"],
        ],
    }


def _itemlist_block() -> List[dict]:
    return [
        {"name": "Item 1", "url": ""},
        {"name": "Item 2", "url": ""},
        {"name": "Item 3", "url": ""},
        {"name": "Item 4", "url": ""},
        {"name": "Item 5", "url": ""},
    ]


def _references_for(page: dict) -> List[dict]:
    url = page["url"]
    section = page.get("section") or _infer_section(url)

    def ref(title: str, link: str, note: str = "") -> dict:
        return {"title": title, "url": link, "note": note}

    common = [
        ref(
            "Google Search Central: Structured data",
            "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data",
        ),
        ref(
            "Google Search Central: SEO starter guide",
            "https://developers.google.com/search/docs/fundamentals/seo-starter-guide",
        ),
    ]

    if section == "github-pages":
        refs = [
            ref("GitHub Docs: GitHub Pages", "https://docs.github.com/en/pages"),
            ref(
                "GitHub Docs: Managing a custom domain for your GitHub Pages site",
                "https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site",
            ),
            ref("Jekyll Docs", "https://jekyllrb.com/docs/"),
            ref("Hugo Docs", "https://gohugo.io/documentation/"),
            ref("Next.js Docs", "https://nextjs.org/docs"),
            ref("React Docs", "https://react.dev/learn"),
        ]
        return (refs + common)[:7]

    if section == "open-source":
        refs = [
            ref(
                "GitHub Docs: Finding ways to contribute to open source on GitHub",
                "https://docs.github.com/en/get-started/exploring-projects-on-github/finding-ways-to-contribute-to-open-source-on-github",
            ),
            ref("GitHub Open Source Guides", "https://opensource.guide/"),
            ref("The Linux Foundation: Open Source Guides", "https://www.linuxfoundation.org/resources/open-source-guides"),
            ref("Open Source Initiative: Licenses", "https://opensource.org/licenses"),
            ref("SPDX License List", "https://spdx.org/licenses/"),
            ref("choosealicense.com", "https://choosealicense.com/"),
            ref("Hacktoberfest", "https://hacktoberfest.com/"),
            ref("Outreachy", "https://www.outreachy.org/"),
            ref("Google Summer of Code", "https://summerofcode.withgoogle.com/"),
        ]
        return (refs + common)[:8]

    if section == "devops-engineer":
        refs = [
            ref("DORA: Research", "https://dora.dev/research/"),
            ref("AWS: DevOps", "https://aws.amazon.com/devops/"),
            ref("Microsoft Learn: Azure DevOps", "https://learn.microsoft.com/en-us/azure/devops/"),
            ref("Kubernetes Documentation", "https://kubernetes.io/docs/"),
            ref("CNCF: Cloud Native Landscape", "https://landscape.cncf.io/"),
            ref("Stack Overflow Developer Survey", "https://survey.stackoverflow.co/"),
        ]
        return (refs + common)[:7]

    if section == "sdlc":
        refs = [
            ref("NIST: Secure Software Development Framework (SSDF)", "https://csrc.nist.gov/Projects/ssdf"),
            ref("OWASP SAMM", "https://owaspsamm.org/"),
            ref("Atlassian: SDLC", "https://www.atlassian.com/software-development/sdlc"),
            ref("Microsoft: SDL (Security Development Lifecycle)", "https://www.microsoft.com/en-us/securityengineering/sdl"),
            ref(
                "IEEE: Software Engineering Body of Knowledge",
                "https://www.computer.org/education/bodies-of-knowledge/software-engineering",
            ),
        ]
        return (refs + common)[:7]

    if section == "unit-testing":
        refs = [
            ref("xUnit.net Documentation", "https://xunit.net/"),
            ref("JUnit 5 User Guide", "https://junit.org/junit5/docs/current/user-guide/"),
            ref("pytest Documentation", "https://docs.pytest.org/en/stable/"),
            ref("Jest Documentation", "https://jestjs.io/docs/getting-started"),
            ref("Martin Fowler: Unit Test", "https://martinfowler.com/bliki/UnitTest.html"),
        ]
        return (refs + common)[:7]

    if section == "product-management":
        refs = [
            ref("Atlassian: Product management", "https://www.atlassian.com/agile/product-management"),
            ref("PMI: Standards & Publications", "https://www.pmi.org/standards"),
            ref(
                "Google: OKRs guide",
                "https://rework.withgoogle.com/guides/set-goals-with-okrs/steps/introduction/",
            ),
            ref("Scrum Guide", "https://scrumguides.org/"),
            ref("Harvard Business Review", "https://hbr.org/"),
        ]
        return (refs + common)[:7]

    return common


def _render_references_block(refs: List[dict]) -> str:
    lines = ["## References", ""]
    for i, r in enumerate(refs, 1):
        note = f" - {r['note']}" if r.get("note") else ""
        lines.append(f"{i}. [{r['title']}]({r['url']}){note}")
    lines.append("")
    return "\n".join(lines)


def _render_body(page: dict, title: str) -> str:
    page_type = page["type"]
    keyword = page.get("keyword") or ""

    if page_type == "trust":
        return "\n".join(
            [
                "## Summary",
                "",
                "Write a clear, policy-style summary for this page.",
                "",
                _render_references_block(_references_for(page)),
            ]
        )

    if page_type == "home":
        return "\n".join(
            [
                "## How to Use This Site",
                "",
                "- Pick a category that matches your current goal.",
                "- Start with the Pillar page, then follow the Cluster pages for step-by-step guides.",
                "- Use the References section in each article to verify details from official sources.",
                "",
                "## What You’ll Learn",
                "",
                "- Open source contribution workflows and beginner paths.",
                "- GitHub Pages publishing (domains, redirects, common errors).",
                "- DevOps and SDLC fundamentals for modern teams.",
                "- Unit testing best practices and toolchains.",
                "- Product management skills, frameworks, and tools.",
                "",
                _render_references_block(_references_for(page)),
            ]
        )

    table = "\n".join(
        [
            "| Option | Best For | Pros | Cons |",
            "|--------|----------|------|------|",
            "| Option A | … | … | … |",
            "| Option B | … | … | … |",
            "| Option C | … | … | … |",
        ]
    )

    return "\n".join(
        [
            f"Intro: Write a short, direct intro for **{keyword or title}**. Add one data point with a citation.",
            "",
            "## Key Takeaways",
            "",
            "- **Definition**: Add a one-sentence definition and why it matters.",
            "- **Practical steps**: Provide an ordered checklist that readers can follow.",
            "- **Pitfalls**: Call out common mistakes and how to avoid them.",
            "- **Decision help**: Include at least one comparison table.",
            "- **Sources**: Cite 5+ authoritative references.",
            "",
            f"## What is {keyword or title}?",
            "",
            "Explain the concept in plain language. Define key terms and scope.",
            "",
            '> "Add an expert quote that supports your key point."',
            "> — Name, Title/Organization (Year)",
            "",
            f"## Why {keyword or title} Matters",
            "",
            "Explain the impact, trade-offs, and who benefits. Add a concrete example.",
            "",
            "## Step-by-Step",
            "",
            "1. Step 1 (with prerequisites)",
            "2. Step 2 (with verification)",
            "3. Step 3 (with troubleshooting)",
            "",
            "## Comparison Table",
            "",
            table,
            "",
            "## Common Mistakes",
            "",
            "1. Mistake 1 — what goes wrong and how to fix it",
            "2. Mistake 2 — what goes wrong and how to fix it",
            "3. Mistake 3 — what goes wrong and how to fix it",
            "",
            _render_references_block(_references_for(page)),
        ]
    )


def _iso_with_tz(dt: datetime) -> str:
    tz8 = timezone(timedelta(hours=8))
    return dt.astimezone(tz8).isoformat(timespec="seconds")


def _merge_keywords(existing: dict, primary: str) -> None:
    if not primary:
        return
    ks = existing.get("keywords")
    if isinstance(ks, list):
        merged = [primary] + [k for k in ks if isinstance(k, str) and k and k != primary]
        existing["keywords"] = merged[:5]
        return
    existing["keywords"] = [primary]


def _build_meta(page: dict, *, date: datetime, draft: bool, title: str, description: str) -> dict:
    page_type = page["type"]
    url = _ensure_trailing_slash(page["url"])
    section = page.get("section") or _infer_section(url)
    keyword = page.get("keyword") or ""

    meta: dict = {
        "title": title,
        "description": description,
        "date": _iso_with_tz(date),
        "draft": bool(draft),
        "commercial_value": 3,
        "affiliate_products": [],
    }

    if page_type == "trust":
        meta["url"] = url

    _merge_keywords(meta, keyword)

    if page_type in {"cluster", "extension"} and section:
        meta["pillar"] = f"/{section}/"

    if page.get("priority"):
        meta["priority"] = page["priority"]

    if page_type in {"pillar", "cluster"}:
        meta["faq"] = _faq_block(keyword or title, 5)
    elif page_type == "extension":
        meta["faq"] = _faq_block(keyword or title, 3)

    schema = page.get("schema") or []
    if "HowTo" in schema:
        meta["howto"] = _howto_block(title)
    if "Table" in schema:
        meta["comparison_table"] = _comparison_table_block(title)
    if "ItemList" in schema:
        meta["itemlist"] = _itemlist_block()

    if url == "/about/":
        meta.setdefault(
            "people",
            [
                {
                    "name": "Editorial Team",
                    "description": "Placeholder editor bio. Replace with real team members and credentials.",
                    "url": "",
                }
            ],
        )

    return meta


def _sync_meta(existing: dict, desired: dict, *, overwrite: bool) -> dict:
    meta = dict(existing)

    # title/description 默认不强制覆盖（避免误伤已写好的内容）
    if overwrite:
        meta["title"] = desired.get("title", meta.get("title"))
        meta["description"] = desired.get("description", meta.get("description"))
    else:
        meta.setdefault("title", desired.get("title"))
        meta.setdefault("description", desired.get("description"))

    # 不强制覆盖 date/draft（发布节奏由人工控制）
    meta.setdefault("date", desired.get("date"))
    meta.setdefault("draft", desired.get("draft", True))

    for k in ["url", "pillar", "priority", "commercial_value", "affiliate_products", "faq", "howto", "comparison_table", "itemlist", "people"]:
        if k in desired and desired[k] not in (None, "", [], {}):
            if overwrite or k not in meta or meta.get(k) in (None, "", [], {}):
                meta[k] = desired[k]

    _merge_keywords(meta, desired.get("keywords", [""])[0] if isinstance(desired.get("keywords"), list) else "")
    return meta


@dataclass(frozen=True)
class WriteResult:
    path: Path
    created: bool
    updated: bool


def write_page(
    page: dict,
    *,
    schedule_cursor: datetime,
    draft: bool,
    overwrite: bool,
    sync: bool,
) -> WriteResult:
    url = _ensure_trailing_slash(page["url"])
    page_type = page["type"]
    keyword = page.get("keyword") or ""

    out_path = _url_to_path(url, page_type)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        raw = out_path.read_text(encoding="utf-8")
        existing_meta, existing_body = _parse_frontmatter(raw)

        title = str(existing_meta.get("title") or "").strip() or _guess_title(page_type, keyword)
        desc = str(existing_meta.get("description") or "").strip() or _guess_description(page_type, keyword)

        desired_meta = _build_meta(page, date=schedule_cursor, draft=draft, title=title, description=desc)

        meta = existing_meta
        if sync or overwrite:
            meta = _sync_meta(existing_meta, desired_meta, overwrite=overwrite)

        body = existing_body
        is_published = existing_meta.get("draft") is False
        should_replace = overwrite or (not is_published and _is_placeholder(existing_body))
        if should_replace:
            body = _render_body(page, title)
        else:
            if "\n## References\n" not in ("\n" + existing_body):
                body = existing_body.rstrip() + "\n\n" + _render_references_block(_references_for(page))

        new_raw = _dump_frontmatter(meta) + body.strip() + "\n"
        if new_raw != raw:
            out_path.write_text(new_raw, encoding="utf-8")
            return WriteResult(out_path, created=False, updated=True)
        return WriteResult(out_path, created=False, updated=False)

    # new file
    title = _guess_title(page_type, keyword)
    desc = _guess_description(page_type, keyword)
    meta = _build_meta(page, date=schedule_cursor, draft=draft, title=title, description=desc)
    body = _render_body(page, title)
    out_path.write_text(_dump_frontmatter(meta) + body.strip() + "\n", encoding="utf-8")
    return WriteResult(out_path, created=True, updated=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="data/content_plan_181.yaml")
    parser.add_argument("--sections", default="", help="逗号分隔，如 open-source,github-pages")
    parser.add_argument("--types", default="", help="逗号分隔，如 pillar,cluster,extension,trust,home")
    parser.add_argument("--draft", choices=["true", "false"], default="true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-sync", action="store_true", help="existing files: do not update frontmatter/sections")
    parser.add_argument("--schedule-start", default="", help="ISO 时间，如 2026-01-01T08:00:00+08:00")
    parser.add_argument("--interval-minutes", type=int, default=90)
    args = parser.parse_args()

    plan_path = Path(args.plan)
    data = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    pages = data.get("pages") or []

    wanted_sections = {s.strip() for s in args.sections.split(",") if s.strip()}
    wanted_types = {t.strip() for t in args.types.split(",") if t.strip()}

    filtered = []
    for p in pages:
        if wanted_sections and p.get("section") not in wanted_sections:
            continue
        if wanted_types and p.get("type") not in wanted_types:
            continue
        filtered.append(p)

    draft = args.draft == "true"
    sync = not args.no_sync

    now = datetime.now(timezone.utc)
    if args.schedule_start:
        start = datetime.fromisoformat(args.schedule_start.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    else:
        start = now + timedelta(days=7)

    cursor = start
    created = updated = unchanged = 0

    for page in filtered:
        res = write_page(
            page,
            schedule_cursor=cursor,
            draft=draft,
            overwrite=args.overwrite,
            sync=sync,
        )
        if res.created:
            created += 1
        if res.updated:
            updated += 1
        else:
            unchanged += 1

        cursor = cursor + timedelta(minutes=max(10, args.interval_minutes))

    print(f"pages={len(filtered)} created={created} updated={updated} unchanged={unchanged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
