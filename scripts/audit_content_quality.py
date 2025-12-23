#!/usr/bin/env python3
"""
内容质量审计（对齐 content_plan_181.yaml）

用途：
1) 检查每个页面是否达到最低字数（min_words）
2) 检查是否包含关键结构（Key Takeaways、References、表格等）
3) 检查 References 是否满足 5+（写作规范的硬性要求）

说明：
- 这是一个“守门员”脚本：输出问题清单 + 退出码（CI/本地都可用）。
- 采用启发式解析 Markdown（不依赖第三方 Markdown 解析器），以稳定为主。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml


PLAN_PATH = Path("data/content_plan_181.yaml")
CONTENT_DIR = Path("content")


WORD_RE = re.compile(r"\b\w+\b")


@dataclass(frozen=True)
class AuditIssue:
    code: str
    message: str


@dataclass(frozen=True)
class PageAudit:
    url: str
    page_type: str
    path: Path
    min_words: int
    words: int
    refs: int
    issues: Tuple[AuditIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


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


def _count_words(body: str) -> int:
    return len(WORD_RE.findall(body))


def _count_references(body: str) -> int:
    if "## References" not in body:
        return 0
    after = body.split("## References", 1)[1]
    # stop at next H2
    after = re.split(r"\n##\s+", after)[0]
    # numbered list or bullet list
    n = len(re.findall(r"^\s*\d+\.\s+\[", after, flags=re.M))
    n += len(re.findall(r"^\s*-\s+\[", after, flags=re.M))
    return n


def _has_key_takeaways(body: str) -> bool:
    return "## Key Takeaways" in body


def _has_table(body: str) -> bool:
    lines = body.splitlines()
    for i in range(len(lines) - 1):
        if "|" in lines[i] and re.search(r"\|\s*[-:]{3,}", lines[i + 1]):
            return True
    return False


def _blockquote_count(body: str) -> int:
    return sum(1 for ln in body.splitlines() if ln.lstrip().startswith(">"))


def _ordered_list_count(body: str) -> int:
    return len(re.findall(r"^\s*\d+\.\s+\S+", body, flags=re.M))


def _faq_count(meta: Dict[str, Any]) -> int:
    faq = meta.get("faq")
    if not isinstance(faq, list):
        return 0
    # count only valid pairs
    out = 0
    for item in faq:
        if isinstance(item, dict) and item.get("question") and item.get("answer"):
            out += 1
    return out


def _required_faq_count(page_type: str) -> int:
    if page_type in {"pillar", "cluster"}:
        return 5
    if page_type == "extension":
        return 3
    return 0


def audit_page(page: Dict[str, Any]) -> PageAudit:
    url = page["url"]
    page_type = page["type"]
    min_words = int(page.get("min_words") or 0)
    path = _url_to_path(url, page_type)

    issues: List[AuditIssue] = []
    if not path.exists():
        issues.append(AuditIssue("missing_file", f"文件不存在：{path}"))
        return PageAudit(url, page_type, path, min_words, 0, 0, tuple(issues))

    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)

    words = _count_words(body)
    refs = _count_references(body)

    # frontmatter sanity
    for key in ("title", "description", "date", "draft"):
        if key not in meta:
            issues.append(AuditIssue("frontmatter_missing", f"缺少 frontmatter 字段：{key}"))

    if page_type == "trust" and "url" not in meta:
        issues.append(AuditIssue("frontmatter_missing", "信任页缺少 url 字段（用于固定 permalink）"))

    if page_type in {"cluster", "extension"} and not meta.get("pillar"):
        issues.append(AuditIssue("frontmatter_missing", "Cluster/扩展页建议填写 pillar"))

    # min words
    if min_words and words < min_words:
        issues.append(AuditIssue("min_words", f"字数不足：{words} < {min_words}（差 {min_words - words}）"))

    # required elements (写作规范偏硬约束：Key Takeaways + References 5+)
    if page_type in {"pillar", "cluster", "extension"}:
        if not _has_key_takeaways(body):
            issues.append(AuditIssue("missing_section", "缺少 ## Key Takeaways"))
        if refs < 5:
            issues.append(AuditIssue("refs", f"References 不足 5 条：{refs}"))
        if not _has_table(body) and page_type in {"pillar", "cluster"}:
            issues.append(AuditIssue("table", "Pillar/Cluster 至少需要 1 个对比表格"))

        required_faq = _required_faq_count(page_type)
        faq_count = _faq_count(meta)
        if faq_count < required_faq:
            issues.append(AuditIssue("faq", f"FAQ 不足：{faq_count} < {required_faq}"))

        # 引用/步骤为软约束，但仍做提示
        bq = _blockquote_count(body)
        if page_type == "pillar" and bq < 3:
            issues.append(AuditIssue("quote", f"Pillar 建议 3+ 引用块，目前 {bq}"))
        if page_type == "cluster" and bq < 2:
            issues.append(AuditIssue("quote", f"Cluster 建议 2+ 引用块，目前 {bq}"))
        if page_type == "extension" and bq < 1:
            issues.append(AuditIssue("quote", f"扩展页建议 1+ 引用块，目前 {bq}"))

        steps = _ordered_list_count(body)
        if page_type in {"pillar", "cluster"} and steps < 3:
            issues.append(AuditIssue("steps", f"Step-by-step 建议至少 3 步，目前检测到 {steps} 条有序列表项"))

    # home / trust：References 5+（规范硬要求）
    if page_type in {"home", "trust"} and refs < 5:
        issues.append(AuditIssue("refs", f"References 不足 5 条：{refs}"))

    return PageAudit(url, page_type, path, min_words, words, refs, tuple(issues))


def load_plan(path: Path) -> List[Dict[str, Any]]:
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or "pages" not in obj:
        raise ValueError(f"非法计划文件：{path}")
    pages = obj["pages"]
    if not isinstance(pages, list):
        raise ValueError(f"非法 pages 字段：{path}")
    return pages


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default=str(PLAN_PATH))
    parser.add_argument("--fail-fast", action="store_true", help="遇到首个失败就退出")
    parser.add_argument("--limit", type=int, default=0, help="仅输出前 N 个失败页面（0=不限）")
    args = parser.parse_args(argv)

    plan_pages = load_plan(Path(args.plan))

    audits: List[PageAudit] = []
    for page in plan_pages:
        audits.append(audit_page(page))
        if args.fail_fast and audits[-1].issues:
            break

    failed = [a for a in audits if a.issues]
    ok = len(audits) - len(failed)

    print(f"audited={len(audits)} ok={ok} failed={len(failed)}")

    # sort by biggest word deficit first (when applicable)
    def deficit(a: PageAudit) -> int:
        return max(0, a.min_words - a.words)

    failed_sorted = sorted(failed, key=lambda a: (deficit(a), len(a.issues)), reverse=True)
    if args.limit and args.limit > 0:
        failed_sorted = failed_sorted[: args.limit]

    for a in failed_sorted:
        print(f"\n- {a.page_type} {a.url} -> {a.path}")
        print(f"  words={a.words} min_words={a.min_words} refs={a.refs}")
        for issue in a.issues:
            print(f"  - [{issue.code}] {issue.message}")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

