#!/usr/bin/env python3
"""
基于 TF-IDF 生成智能内链数据，输出到 data/internal_links.json

设计目标：
1) 只基于“已发布内容”（draft=false 且 date<=now）计算
2) 输出稳定（同样输入得到同样输出），避免每次构建内链随机变化
3) 增量更新策略：平时只更新“新发布文章”，周五全量刷新（避免旧页面频繁变动）

说明：
- 状态文件默认写入 `.cache/internal_links/update_state.json`（建议配合 GitHub Actions cache 持久化）
- 输出格式遵循《Hugo PBN 建站手册》：每个 URL 对应 { links: [...], updated: "..." }
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml


CONTENT_DIR = Path("content")
OUTPUT_FILE = Path("data/internal_links.json")
DEFAULT_CACHE_DIR = Path(".cache")
FULL_UPDATE_TZ = timezone(timedelta(hours=8))

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
    content_type: str
    pillar_url: str | None
    published_at_utc: datetime | None


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
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
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


def _is_full_update_day(full_update_day: int, now_utc: datetime) -> bool:
    """是否到了全量刷新日（按 +08:00 计算周几，避免 UTC 跨日导致误判）。"""
    return now_utc.astimezone(FULL_UPDATE_TZ).weekday() == full_update_day


def _get_last_full_update(state_path: Path) -> datetime | None:
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return _parse_datetime(data.get("last_full_update"))


def _save_full_update_state(state_path: Path, now_utc: datetime) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    now_str = now_utc.isoformat().replace("+00:00", "Z")
    state_path.write_text(
        json.dumps({"last_full_update": now_str}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_docs(now: datetime) -> List[PageDoc]:
    docs: List[PageDoc] = []

    for md_path in sorted(CONTENT_DIR.rglob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        meta, body = _strip_frontmatter(raw)

        url = _path_to_url(md_path, meta)
        section = md_path.relative_to(CONTENT_DIR).parts[0] if md_path != CONTENT_DIR / "_index.md" else ""
        published_at_utc = _parse_datetime(meta.get("date"))
        content_type = str(meta.get("type") or "").strip()
        pillar_url = None
        if isinstance(meta.get("pillar"), str) and meta["pillar"].strip():
            pillar_url = _ensure_trailing_slash(meta["pillar"].strip())

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
                content_type=content_type,
                pillar_url=pillar_url,
                published_at_utc=published_at_utc,
            )
        )

    return docs


def _build_tfidf(docs: List[PageDoc]) -> List[Dict[str, float]]:
    doc_terms: List[Counter[str]] = []
    df: Counter[str] = Counter()

    for doc in docs:
        tokens = _tokenize(doc.text)
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

    return vectors


def _compute_related(
    docs: List[PageDoc],
    vectors: List[Dict[str, float]],
    limit: int,
) -> Dict[str, List[dict]]:
    index_by_url: Dict[str, int] = {d.url: i for i, d in enumerate(docs)}
    cluster_urls_by_pillar: Dict[str, List[str]] = defaultdict(list)
    for d in docs:
        if d.pillar_url:
            cluster_urls_by_pillar[d.pillar_url].append(d.url)

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

        def score_by_url(url: str) -> float:
            idx = index_by_url.get(url)
            return float(scores.get(idx, 0.0)) if idx is not None else 0.0

        def is_pillar_like(d: PageDoc) -> bool:
            # 兼容：有些分区 _index.md 可能没有显式写 type: pillar
            return d.content_type == "pillar" or d.source_path.name == "_index.md"

        def push_url(url: str, *, force: bool) -> None:
            if url == doc.url:
                return
            idx = index_by_url.get(url)
            if idx is None:
                return
            if url in seen:
                return
            s = score_by_url(url)
            if not force and s <= 0:
                return
            seen.add(url)
            links.append(
                {
                    "url": url,
                    "title": docs[idx].title,
                    "score": round(float(s), 4),
                }
            )

        links: List[dict] = []
        seen: set[str] = set()

        # 1) Cluster/Extension：优先链回 Pillar（结构性关系，比相似度更重要）
        if doc.pillar_url:
            push_url(doc.pillar_url, force=True)

        # 2) Pillar：优先链向属于自己的 Cluster（按相似度排序，保证确定性）
        if is_pillar_like(doc):
            cluster_urls = cluster_urls_by_pillar.get(doc.url, [])
            cluster_urls_sorted = sorted(cluster_urls, key=lambda u: (-score_by_url(u), u))
            for u in cluster_urls_sorted:
                if len(links) >= limit:
                    break
                push_url(u, force=True)

        # 3) Cluster：同一 Pillar 下的内容优先
        if doc.pillar_url and len(links) < limit:
            for j, _score in ranked:
                if len(links) >= limit:
                    break
                other = docs[j]
                if other.pillar_url == doc.pillar_url and other.url != doc.pillar_url:
                    push_url(other.url, force=False)

        # 4) 兜底：按相似度补齐
        for j, _score in ranked:
            if len(links) >= limit:
                break
            push_url(docs[j].url, force=False)

        related[doc.url] = links

    return related


def _load_existing(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--incremental", action="store_true", help="增量更新：仅更新新发布文章（周五全量刷新）")
    parser.add_argument("--force-full", action="store_true", help="强制全量刷新（忽略周几与状态文件）")
    parser.add_argument(
        "--full-update-day",
        type=int,
        default=4,  # Friday
        choices=range(7),
        metavar="DAY",
        help="全量刷新日（0=周一...4=周五）。默认：4（周五，按 +08:00 计算）。",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(DEFAULT_CACHE_DIR),
        help="缓存目录（保存 last_full_update 状态）。默认：.cache",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    docs = _load_docs(now)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not docs:
        out_path.write_text("{}", encoding="utf-8")
        return 0

    cache_dir = Path(args.cache_dir)
    state_path = cache_dir / "internal_links" / "update_state.json"

    is_full_update = True
    last_full_update: datetime | None = None
    if args.incremental and not args.force_full:
        if _is_full_update_day(args.full_update_day, now):
            is_full_update = True
        else:
            last_full_update = _get_last_full_update(state_path)
            is_full_update = last_full_update is None

    vectors = _build_tfidf(docs)
    new_links = _compute_related(docs, vectors, limit=max(1, args.limit))
    now_str = now.isoformat().replace("+00:00", "Z")

    old = _load_existing(out_path)

    if is_full_update:
        full = {url: {"links": links, "updated": now_str} for url, links in sorted(new_links.items())}
        out_path.write_text(json.dumps(full, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _save_full_update_state(state_path, now)
        return 0

    # 增量：仅更新“新发布文章”（以及缺失条目）
    urls_to_update: set[str] = set()
    if last_full_update:
        for d in docs:
            if d.url not in old:
                urls_to_update.add(d.url)
                continue
            if d.published_at_utc and d.published_at_utc > last_full_update:
                urls_to_update.add(d.url)

    merged: dict[str, dict] = {}
    for url, links in sorted(new_links.items()):
        if url in urls_to_update:
            merged[url] = {"links": links, "updated": now_str}
            continue
        prev = old.get(url)
        if isinstance(prev, dict) and isinstance(prev.get("links"), list):
            merged[url] = prev
        else:
            merged[url] = {"links": links, "updated": now_str}

    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
