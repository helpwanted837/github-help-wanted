#!/usr/bin/env python3
"""
批量修改 Hugo Markdown 的 YAML frontmatter（支持 dry-run）。

目标（对应 DEVELOPER_TASKS / F3）：
- 支持批量修改 date / draft / keywords 等字段
- 支持按目录/路径筛选、按关键词筛选、按字段匹配筛选
- 支持 dry-run 预览，避免误改

安全策略：
- 默认 dry-run（不写文件），只有加 --apply 才会落盘
- 仅修改 frontmatter（--- ... ---），正文保持原样
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Change:
    key: str
    before: object
    after: object


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _split_frontmatter(raw: str) -> tuple[dict[str, Any] | None, str, bool]:
    if not raw.startswith("---"):
        return None, raw, False
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None, raw, False
    _sep, fm, body = parts
    meta = yaml.safe_load(fm) or {}
    if not isinstance(meta, dict):
        return None, raw, False
    return meta, body.lstrip("\n"), True


def _dump_frontmatter(meta: dict[str, Any]) -> str:
    dumped = yaml.safe_dump(
        meta,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    )
    dumped = dumped.rstrip() + "\n"
    return f"---\n{dumped}---\n"


def _infer_scalar(value: str) -> object:
    v = value.strip()
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    if re.fullmatch(r"-?\\d+", v):
        try:
            return int(v)
        except ValueError:
            return v
    if re.fullmatch(r"-?\\d+\\.\\d+", v):
        try:
            return float(v)
        except ValueError:
            return v
    return v


def _parse_kv(arg: str) -> tuple[str, str]:
    if "=" not in arg:
        raise ValueError(f"参数格式错误（需要 key=value）：{arg}")
    key, value = arg.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        raise ValueError(f"参数格式错误（key 为空）：{arg}")
    return key, value


def _split_key_path(key: str) -> list[str]:
    return [p for p in key.split(".") if p.strip()]


def _get_by_path(meta: dict[str, Any], key_path: list[str]) -> object:
    cur: object = meta
    for k in key_path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _ensure_parent_dict(meta: dict[str, Any], key_path: list[str]) -> tuple[dict[str, Any] | None, str]:
    if not key_path:
        return None, ""
    parent: dict[str, Any] = meta
    for k in key_path[:-1]:
        cur = parent.get(k)
        if cur is None:
            nxt: dict[str, Any] = {}
            parent[k] = nxt
            parent = nxt
            continue
        if not isinstance(cur, dict):
            return None, key_path[-1]
        parent = cur
    return parent, key_path[-1]


def _contains_keyword(value: object, keyword: str) -> bool:
    """
    在 keywords 字段的任意层级（str/list/dict）做“大小写不敏感包含”匹配。
    """
    if not keyword:
        return True
    needle = keyword.lower()

    if isinstance(value, str):
        return needle in value.lower()
    if isinstance(value, list):
        return any(_contains_keyword(v, keyword) for v in value)
    if isinstance(value, dict):
        return any(_contains_keyword(v, keyword) for v in value.values())
    return False


def _match_filters(
    *,
    rel_path: str,
    meta: dict[str, Any],
    path_prefix: str,
    path_regex: str,
    keyword: str,
    where: list[str],
) -> bool:
    if path_prefix and not rel_path.startswith(path_prefix):
        return False
    if path_regex:
        if not re.search(path_regex, rel_path):
            return False

    if keyword:
        kws = meta.get("keywords")
        if not _contains_keyword(kws, keyword):
            return False

    for expr in where:
        k, v = _parse_kv(expr)
        cur = _get_by_path(meta, _split_key_path(k))
        if isinstance(cur, list):
            if not any(isinstance(x, str) and x == v for x in cur):
                return False
        else:
            if str(cur or "").strip() != v:
                return False

    return True


def _apply_changes(
    meta: dict[str, Any],
    *,
    set_values: list[str],
    set_lists: list[str],
    add_list: list[str],
    remove_list: list[str],
    delete_keys: list[str],
) -> list[Change]:
    changes: list[Change] = []

    for expr in set_values:
        key, value = _parse_kv(expr)
        key_path = _split_key_path(key)
        before = _get_by_path(meta, key_path)
        after = _infer_scalar(value)
        if before != after:
            parent, leaf = _ensure_parent_dict(meta, key_path)
            if parent is None:
                print(f"::warning::跳过 set（路径不是 dict）：{key}", file=sys.stderr)
                continue
            parent[leaf] = after
            changes.append(Change(key=key, before=before, after=after))

    for expr in set_lists:
        key, value = _parse_kv(expr)
        key_path = _split_key_path(key)
        items = [x.strip() for x in value.split(",") if x.strip()]
        before = _get_by_path(meta, key_path)
        after = items
        if before != after:
            parent, leaf = _ensure_parent_dict(meta, key_path)
            if parent is None:
                print(f"::warning::跳过 set-list（路径不是 dict）：{key}", file=sys.stderr)
                continue
            if before is not None and not isinstance(before, list):
                print(f"::warning::跳过 set-list（原值不是 list）：{key}", file=sys.stderr)
                continue
            parent[leaf] = after
            changes.append(Change(key=key, before=before, after=after))

    for expr in add_list:
        key, value = _parse_kv(expr)
        key_path = _split_key_path(key)
        item = value.strip()
        if not item:
            continue
        before = _get_by_path(meta, key_path)
        if before is not None and not isinstance(before, list):
            print(f"::warning::跳过 add-list（原值不是 list）：{key}", file=sys.stderr)
            continue
        cur = before if isinstance(before, list) else []
        cur_norm = [x for x in cur if isinstance(x, str)]
        if item in cur_norm:
            continue
        after = cur_norm + [item]
        parent, leaf = _ensure_parent_dict(meta, key_path)
        if parent is None:
            print(f"::warning::跳过 add-list（路径不是 dict）：{key}", file=sys.stderr)
            continue
        parent[leaf] = after
        changes.append(Change(key=key, before=before, after=after))

    for expr in remove_list:
        key, value = _parse_kv(expr)
        key_path = _split_key_path(key)
        item = value.strip()
        if not item:
            continue
        before = _get_by_path(meta, key_path)
        if not isinstance(before, list):
            continue
        cur_norm = [x for x in before if isinstance(x, str)]
        if item not in cur_norm:
            continue
        after = [x for x in cur_norm if x != item]
        parent, leaf = _ensure_parent_dict(meta, key_path)
        if parent is None:
            print(f"::warning::跳过 remove-list（路径不是 dict）：{key}", file=sys.stderr)
            continue
        parent[leaf] = after
        changes.append(Change(key=key, before=before, after=after))

    for key in delete_keys:
        k = key.strip()
        if not k:
            continue
        key_path = _split_key_path(k)
        parent, leaf = _ensure_parent_dict(meta, key_path)
        if parent is None:
            continue
        if leaf in parent:
            before = parent.get(leaf)
            del parent[leaf]
            changes.append(Change(key=k, before=before, after=None))

    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-dir", default="content", help="内容根目录（默认 content/）。")
    parser.add_argument("--path-prefix", default="", help="仅处理该前缀路径（相对 content/）。例：open-source/。")
    parser.add_argument("--path-regex", default="", help="仅处理路径匹配该正则的文件（相对 content/）。")
    parser.add_argument("--keyword", default="", help="仅处理 keywords 包含该关键词的文章。")
    parser.add_argument("--where", action="append", default=[], help="筛选条件（可重复）：key=value。list 字段表示“包含”。")
    parser.add_argument("--set", action="append", default=[], help="设置字段（可重复）：key=value（支持 true/false/int/float）。")
    parser.add_argument("--set-list", action="append", default=[], help="设置列表字段：key=a,b,c（覆盖原值）。")
    parser.add_argument("--add-list", action="append", default=[], help="向列表字段追加：key=item（去重）。")
    parser.add_argument("--remove-list", action="append", default=[], help="从列表字段移除：key=item。")
    parser.add_argument("--delete", action="append", default=[], help="删除字段（可重复）：key。")
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少个文件（0=不限）。")
    parser.add_argument("--apply", action="store_true", help="实际写入文件（默认 dry-run）。")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    content_dir = (repo_root / args.content_dir).resolve()
    if not content_dir.exists():
        print(f"内容目录不存在：{content_dir}", file=sys.stderr)
        return 2

    path_prefix = args.path_prefix.strip().lstrip("/")
    if path_prefix and not path_prefix.endswith("/"):
        path_prefix += "/"

    candidates = [p for p in sorted(content_dir.rglob("*.md")) if p.is_file()]
    if int(args.limit) > 0:
        candidates = candidates[: int(args.limit)]

    matched = 0
    changed = 0

    for md_path in candidates:
        rel_path = str(md_path.relative_to(content_dir)).replace("\\\\", "/")
        raw = _read_text(md_path)
        meta, body, ok = _split_frontmatter(raw)
        if not ok or meta is None:
            continue

        if not _match_filters(
            rel_path=rel_path,
            meta=meta,
            path_prefix=path_prefix,
            path_regex=str(args.path_regex or "").strip(),
            keyword=str(args.keyword or "").strip(),
            where=list(args.where or []),
        ):
            continue

        matched += 1
        changes = _apply_changes(
            meta,
            set_values=list(args.set or []),
            set_lists=list(args.set_list or []),
            add_list=list(args.add_list or []),
            remove_list=list(args.remove_list or []),
            delete_keys=list(args.delete or []),
        )
        if not changes:
            continue

        changed += 1
        if args.apply:
            new_raw = _dump_frontmatter(meta) + body.lstrip("\n")
            _write_text(md_path, new_raw)
        else:
            print(f"[DRY-RUN] {rel_path}")
        for c in changes:
            before = c.before if c.before is not None else "∅"
            after = c.after if c.after is not None else "∅"
            print(f"  - {c.key}: {before!r} -> {after!r}")

    mode = "apply" if args.apply else "dry-run"
    print(f"\nDone ({mode}): matched={matched} changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
