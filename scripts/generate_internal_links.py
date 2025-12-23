#!/usr/bin/env python3
"""
基于 TF-IDF 生成智能内链数据，输出到 data/internal_links.json

设计目标：
1) 只基于“已发布内容”（draft=false 且 date<=now）计算
2) 输出稳定（同样输入得到同样输出），避免每次构建内链随机变化
3) 可增量写入：--incremental 时尽量保留未变化的条目
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml


CONTENT_DIR = Path("content")
OUTPUT_FILE = Path("data/internal_links.json")

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
}


@dataclass(frozen=True)
class PageDoc:
    source_path: Path
    url: str
    title: str
    description: str
    section: str
    text: str


def _strip_frontmatter(raw: str) -> Tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw

    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw

    _, fm, body = parts
    meta = yaml.safe_load(fm) or {}
    return meta, body


def _parse_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def _ensure_trailing_slash(url: str) -> str:
    if url == "/":
        return "/"
    return url if url.endswith("/") else f"{url}/"


def _path_to_url(path: Path, meta: dict) -> str:
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


def _markdown_to_text(md: str) -> str:
    text = md
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"#+\\s*", " ", text)
    return re.sub(r"\\s+", " ", text).strip()


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in STOPWORDS]


def _is_publishable(meta: dict, now: datetime) -> bool:
    if meta.get("draft") is True:
        return False
    dt = _parse_datetime(meta.get("date"))
    if dt is None:
        return True
    return dt <= now


def _load_docs(now: datetime) -> List[PageDoc]:
    docs: List[PageDoc] = []

    for md_path in sorted(CONTENT_DIR.rglob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        meta, body = _strip_frontmatter(raw)

        url = _path_to_url(md_path, meta)
        section = md_path.relative_to(CONTENT_DIR).parts[0] if md_path != CONTENT_DIR / "_index.md" else ""

        if section == "pages":
            continue
        if url == "/":
            continue
        if not _is_publishable(meta, now):
            continue

        title = str(meta.get("title") or "").strip() or url
        description = str(meta.get("description") or "").strip()
        plain = _markdown_to_text(body)
        combined = " ".join([title, description, plain]).strip()

        docs.append(
            PageDoc(
                source_path=md_path,
                url=url,
                title=title,
                description=description,
                section=section,
                text=combined,
            )
        )

    return docs


def _build_tfidf(docs: List[PageDoc]) -> Tuple[List[Dict[str, float]], List[List[str]]]:
    token_lists: List[List[str]] = []
    doc_terms: List[Counter[str]] = []
    df: Counter[str] = Counter()

    for doc in docs:
        tokens = _tokenize(doc.text)
        token_lists.append(tokens)
        counts = Counter(tokens)
        doc_terms.append(counts)
        df.update(set(counts.keys()))

    n = max(len(docs), 1)
    idf: Dict[str, float] = {t: (math.log((n + 1) / (df_t + 1)) + 1.0) for t, df_t in df.items()}

    vectors: List[Dict[str, float]] = []
    for counts in doc_terms:
        vec: Dict[str, float] = {}
        for term, cnt in counts.items():
            tf = 1.0 + math.log(cnt)
            vec[term] = tf * idf.get(term, 0.0)
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({t: (v / norm) for t, v in vec.items()})

    return vectors, token_lists


def _compute_related(
    docs: List[PageDoc],
    vectors: List[Dict[str, float]],
    limit: int,
) -> Dict[str, List[dict]]:
    inverted: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
    for idx, vec in enumerate(vectors):
        for term, weight in vec.items():
            inverted[term].append((idx, weight))

    related: Dict[str, List[dict]] = {}
    for i, doc in enumerate(docs):
        scores: Dict[int, float] = defaultdict(float)
        for term, w_i in vectors[i].items():
            for j, w_j in inverted.get(term, []):
                if j == i:
                    continue
                scores[j] += w_i * w_j

        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], docs[kv[0]].url))
        links: List[dict] = []
        for j, score in ranked[:limit]:
            if score <= 0:
                continue
            links.append(
                {
                    "url": docs[j].url,
                    "title": docs[j].title,
                    "score": round(float(score), 4),
                }
            )

        related[doc.url] = links

    return related


def _load_existing(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _merge_incremental(old: dict, new_links: Dict[str, List[dict]], now: datetime) -> dict:
    merged = {}
    now_str = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    for url, links in sorted(new_links.items()):
        prev = old.get(url)
        if isinstance(prev, dict) and prev.get("links") == links:
            merged[url] = prev
            continue
        merged[url] = {"links": links, "updated": now_str}

    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--incremental", action="store_true")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    docs = _load_docs(now)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not docs:
        out_path.write_text("{}", encoding="utf-8")
        return 0

    vectors, _ = _build_tfidf(docs)
    new_links = _compute_related(docs, vectors, limit=max(1, args.limit))

    if args.incremental:
        old = _load_existing(out_path)
        merged = _merge_incremental(old, new_links, now)
        out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0

    full = {url: {"links": links} for url, links in sorted(new_links.items())}
    out_path.write_text(json.dumps(full, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

