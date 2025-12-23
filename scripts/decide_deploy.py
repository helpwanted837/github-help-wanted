#!/usr/bin/env python3
"""
判断定时任务是否需要部署：
- 仅当存在“未来日期文章”在上一次成功工作流运行之后到期（date<=now）时返回 true
- 用于 GitHub Actions 的 schedule 触发，避免无意义的高频部署
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml


CONTENT_DIR = Path("content")


def parse_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def load_frontmatter(md_path: Path) -> dict:
    raw = md_path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}
    _, fm, _ = parts
    return yaml.safe_load(fm) or {}


def get_last_success_run_time(repo: str, workflow_file: str, token: str) -> datetime | None:
    api = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/runs?status=success&per_page=1"
    req = urllib.request.Request(
        api,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "github-help-wanted-deploy-check",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError):
        return None

    runs = data.get("workflow_runs") or []
    if not runs:
        return None

    ts = runs[0].get("run_started_at") or runs[0].get("created_at") or runs[0].get("updated_at")
    return parse_datetime(ts)


def has_new_publishable_content(since: datetime, now: datetime) -> bool:
    for md_path in CONTENT_DIR.rglob("*.md"):
        meta = load_frontmatter(md_path)
        if meta.get("draft") is True:
            continue
        dt = parse_datetime(meta.get("date"))
        if dt is None:
            continue
        if since < dt <= now:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-file", default="scheduled-deploy.yml")
    args = parser.parse_args()

    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")

    now = datetime.now(timezone.utc)
    since = datetime.min.replace(tzinfo=timezone.utc)

    if repo and token:
        last = get_last_success_run_time(repo, args.workflow_file, token)
        if last:
            since = last

    print("true" if has_new_publishable_content(since, now) else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

