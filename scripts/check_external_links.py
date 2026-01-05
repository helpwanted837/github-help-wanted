#!/usr/bin/env python3
"""
检查 content/ 中引用的外链健康度（HTTP 状态 / 重定向 / 超时）。

设计目标：
- 低依赖：仅使用 Python 标准库，便于在 GitHub Actions 直接运行。
- 尽量准确：忽略 Markdown 代码块中的 URL，减少误报。
- 可追溯：报告中记录“哪个文件引用了哪个链接”，便于快速修复。

退出码：
- 默认仅把 404/410 视为“硬失败”（exit 1），其余错误视为警告（exit 0）。
  这样可以减少短期网络抖动导致的噪音报警。
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urlparse
from urllib.request import Request, urlopen

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


MD_LINK_RE = re.compile(r"\]\((https?://[^)\s]+)", re.IGNORECASE)
AUTO_LINK_RE = re.compile(r"<(https?://[^>]+)>", re.IGNORECASE)
BARE_URL_RE = re.compile(r"(https?://[^\s<>()]+)", re.IGNORECASE)

FENCE_RE = re.compile(r"^\s*(```|~~~)")

DEFAULT_UA = "Mozilla/5.0 (compatible; LinkCheck/1.0)"


@dataclass(frozen=True)
class CheckResult:
    url: str
    status: int | None
    final_url: str | None
    method: str | None
    duration_ms: int
    error: str | None


def _load_site_host(repo_root: Path) -> str | None:
    cfg = repo_root / "hugo.toml"
    if not cfg.exists():
        return None

    try:
        data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return None

    base_url = (data.get("baseURL") or "").strip()
    if not base_url:
        return None

    try:
        parsed = urlparse(base_url)
    except Exception:
        return None

    return (parsed.hostname or "").lower() or None


def _normalize_url(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None

    # Remove surrounding punctuation that commonly appears after URLs.
    raw = raw.strip("()[]{}<>\"'")
    raw = raw.rstrip(".,;:!?)\"'")
    if not raw:
        return None

    # Drop fragment; keep query.
    url, _frag = urldefrag(raw)
    url = url.strip()
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None

    return url


def _is_internal(url: str, internal_hosts: set[str]) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False

    # Remove leading www. for comparisons.
    host_no_www = host[4:] if host.startswith("www.") else host

    for internal in internal_hosts:
        if host == internal or host_no_www == internal:
            return True
        if host.endswith("." + internal) or host_no_www.endswith("." + internal):
            return True

    return False


def _extract_urls_from_markdown(text: str) -> list[str]:
    urls: list[str] = []
    in_fence = False

    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for pattern in (MD_LINK_RE, AUTO_LINK_RE, BARE_URL_RE):
            for match in pattern.finditer(line):
                urls.append(match.group(1))

    return urls


def _probe_once(url: str, timeout: float, user_agent: str) -> CheckResult:
    start = time.monotonic()

    def _do(method: str) -> CheckResult:
        request = Request(
            url,
            method=method,
            headers={
                "User-Agent": user_agent,
                "Accept": "*/*",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                final_url = resp.geturl()
                duration_ms = int((time.monotonic() - start) * 1000)
                return CheckResult(
                    url=url,
                    status=int(status) if status is not None else None,
                    final_url=final_url,
                    method=method,
                    duration_ms=duration_ms,
                    error=None,
                )
        except HTTPError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return CheckResult(
                url=url,
                status=int(getattr(exc, "code", 0) or 0) or None,
                final_url=getattr(exc, "url", None),
                method=method,
                duration_ms=duration_ms,
                error=str(exc),
            )
        except URLError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return CheckResult(
                url=url,
                status=None,
                final_url=None,
                method=method,
                duration_ms=duration_ms,
                error=str(exc),
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return CheckResult(
                url=url,
                status=None,
                final_url=None,
                method=method,
                duration_ms=duration_ms,
                error=f"{type(exc).__name__}: {exc}",
            )

    head = _do("HEAD")
    # 某些站点会对 HEAD 返回 403/405/400，但 GET 是可用的。
    if head.status in {400, 403, 405}:
        return _do("GET")
    return head


def check_url(url: str, timeout: float, user_agent: str, retries: int) -> CheckResult:
    last: CheckResult | None = None
    for attempt in range(retries + 1):
        last = _probe_once(url, timeout=timeout, user_agent=user_agent)
        if last.status is not None and last.status < 500:
            return last
        if last.error is None and last.status is not None:
            return last
        if attempt < retries:
            time.sleep(0.6 * (attempt + 1))
    assert last is not None
    return last


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-dir", default="content", help="内容目录（默认：content）")
    parser.add_argument(
        "--output",
        default=".cache/external_links/report.json",
        help="报告输出路径（默认：.cache/external_links/report.json）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多检查多少个 URL（0 表示全部；用于本地快速验证/降低 CI 压力）",
    )
    parser.add_argument("--timeout", type=float, default=12.0, help="单次请求超时（秒）")
    parser.add_argument("--max-workers", type=int, default=16, help="并发线程数")
    parser.add_argument("--retries", type=int, default=1, help="失败重试次数（默认：1）")
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_UA,
        help="HTTP User-Agent（默认：内置 UA）",
    )
    parser.add_argument(
        "--fail-on-any",
        action="store_true",
        help="只要出现非 2xx/3xx 的链接就失败（默认仅 404/410 失败）",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    content_dir = (repo_root / args.content_dir).resolve()
    if not content_dir.exists():
        print(f"内容目录不存在：{content_dir}", file=sys.stderr)
        return 2

    site_host = _load_site_host(repo_root)
    internal_hosts: set[str] = {h for h in {site_host, "localhost", "127.0.0.1"} if h}

    url_to_files: dict[str, set[str]] = {}
    for md_path in sorted(content_dir.rglob("*.md")):
        try:
            text = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = md_path.read_text(encoding="utf-8", errors="ignore")

        for raw in _extract_urls_from_markdown(text):
            url = _normalize_url(raw)
            if not url:
                continue
            if _is_internal(url, internal_hosts):
                continue
            rel = str(md_path.relative_to(repo_root))
            url_to_files.setdefault(url, set()).add(rel)

    urls = sorted(url_to_files.keys())
    if int(args.limit) > 0:
        urls = urls[: int(args.limit)]
    started_at = datetime.now(timezone.utc).isoformat()

    results: dict[str, CheckResult] = {}
    with futures.ThreadPoolExecutor(max_workers=max(1, int(args.max_workers))) as pool:
        future_map = {
            pool.submit(check_url, url, args.timeout, args.user_agent, int(args.retries)): url for url in urls
        }
        for fut in futures.as_completed(future_map):
            url = future_map[fut]
            try:
                results[url] = fut.result()
            except Exception as exc:
                results[url] = CheckResult(
                    url=url,
                    status=None,
                    final_url=None,
                    method=None,
                    duration_ms=0,
                    error=f"{type(exc).__name__}: {exc}",
                )

    ok = 0
    redirects = 0
    hard_fail = 0
    soft_fail = 0

    for url, res in results.items():
        status = res.status
        if status is None:
            soft_fail += 1
            continue
        if 200 <= status < 400:
            ok += 1
            if res.final_url and res.final_url.rstrip("/") != url.rstrip("/"):
                redirects += 1
            continue
        if status in {404, 410}:
            hard_fail += 1
        else:
            soft_fail += 1

    payload = {
        "started_at": started_at,
        "site_host": site_host,
        "total_urls": len(urls),
        "ok": ok,
        "redirects": redirects,
        "hard_fail": hard_fail,
        "soft_fail": soft_fail,
        "results": [
            {
                "url": url,
                "status": res.status,
                "final_url": res.final_url,
                "method": res.method,
                "duration_ms": res.duration_ms,
                "error": res.error,
                "files": sorted(url_to_files.get(url, set())),
            }
            for url, res in sorted(results.items(), key=lambda x: x[0])
        ],
    }

    _write_json((repo_root / args.output).resolve(), payload)

    print(
        "外链检查完成："
        f"total={len(urls)} ok={ok} redirects={redirects} hard_fail={hard_fail} soft_fail={soft_fail}"
    )

    if args.fail_on_any and (hard_fail > 0 or soft_fail > 0):
        return 1
    if hard_fail > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
