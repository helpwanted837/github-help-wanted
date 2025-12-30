#!/usr/bin/env python3
"""
死链检查（汇总内链 + 外链）并输出统一报告。

设计目标（对应 DEVELOPER_TASKS / F2）：
1) 基于 public/ 产物检查站内死链（复用 check_internal_links.py 的映射规则）
2) 基于 content/ 源文件检查外链健康度（复用 check_external_links.py）
3) 生成统一 JSON 报告，便于 CI/人工排查

默认行为：
- 内链：总是检查，并写出 internal 报告
- 外链：默认检查；可用 --skip-external 跳过（例如避免网络抖动）
- 退出码：默认 0；传 --fail 时，若存在内链死链或外链 hard_fail(404/410) 则 exit 1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", default="public", help="Hugo 构建产物目录（默认 public/）。")
    parser.add_argument("--content-dir", default="content", help="内容目录（默认 content/，用于外链扫描）。")
    parser.add_argument(
        "--output",
        default=".cache/dead_links/report.json",
        help="汇总报告输出路径（默认 .cache/dead_links/report.json）。",
    )
    parser.add_argument("--skip-external", action="store_true", help="仅检查内链，跳过外链检查。")
    parser.add_argument("--external-limit", type=int, default=0, help="外链检查最多检查多少个 URL（0=全部）。")
    parser.add_argument("--external-timeout", type=float, default=12.0, help="外链检查超时（秒）。")
    parser.add_argument("--external-max-workers", type=int, default=16, help="外链检查并发线程数。")
    parser.add_argument("--external-retries", type=int, default=1, help="外链检查失败重试次数。")
    parser.add_argument("--external-fail-on-any", action="store_true", help="外链：任意非 2xx/3xx 都视为失败。")
    parser.add_argument("--fail", action="store_true", help="严格模式：存在死链则返回非 0。")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    scripts_dir = repo_root / "scripts"

    public_dir = (repo_root / str(args.public)).resolve()
    content_dir = (repo_root / str(args.content_dir)).resolve()
    out_path = (repo_root / str(args.output)).resolve()

    internal_report = out_path.parent / "internal_links.json"
    external_report = out_path.parent / "external_links.json"

    internal_script = scripts_dir / "check_internal_links.py"
    external_script = scripts_dir / "check_external_links.py"

    if not public_dir.exists():
        print(f"::error::Missing public dir: {public_dir}")
        return 2
    if not internal_script.exists():
        print(f"::error::Missing script: {internal_script}")
        return 2

    out_path.parent.mkdir(parents=True, exist_ok=True)

    internal_code = _run(
        [
            sys.executable,
            str(internal_script),
            "--public",
            str(public_dir),
            "--report-json",
            str(internal_report),
        ]
    )

    external_code: int | None = None
    if args.skip_external:
        external_code = None
    else:
        if not content_dir.exists():
            print(f"::error::Missing content dir: {content_dir}")
            return 2
        if not external_script.exists():
            print(f"::error::Missing script: {external_script}")
            return 2

        cmd = [
            sys.executable,
            str(external_script),
            "--content-dir",
            str(content_dir),
            "--output",
            str(external_report),
            "--limit",
            str(int(args.external_limit)),
            "--timeout",
            str(float(args.external_timeout)),
            "--max-workers",
            str(int(args.external_max_workers)),
            "--retries",
            str(int(args.external_retries)),
        ]
        if bool(args.external_fail_on_any):
            cmd.append("--fail-on-any")
        external_code = _run(cmd)

    internal_payload = _read_json(internal_report)
    external_payload = _read_json(external_report) if external_code is not None else {}

    internal_broken_targets = int(internal_payload.get("broken_targets") or 0)
    internal_broken_refs = int(internal_payload.get("broken_references") or 0)

    external_hard_fail = int(external_payload.get("hard_fail") or 0) if external_payload else 0
    external_soft_fail = int(external_payload.get("soft_fail") or 0) if external_payload else 0
    external_total = int(external_payload.get("total_urls") or 0) if external_payload else 0

    summary = {
        "generated_at_utc": _utc_now_iso(),
        "public_dir": str(public_dir),
        "content_dir": str(content_dir),
        "internal": {
            "exit_code": internal_code,
            "broken_targets": internal_broken_targets,
            "broken_references": internal_broken_refs,
            "report": str(internal_report),
        },
        "external": {
            "enabled": external_code is not None,
            "exit_code": external_code,
            "total_urls": external_total,
            "hard_fail": external_hard_fail,
            "soft_fail": external_soft_fail,
            "report": str(external_report) if external_code is not None else "",
        },
        "combined_report": str(out_path),
    }

    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "dead_links: "
        f"internal_targets={internal_broken_targets} internal_refs={internal_broken_refs} "
        f"external_total={external_total} external_hard_fail={external_hard_fail} external_soft_fail={external_soft_fail}"
    )
    print(f"dead_links: report={out_path}")

    if not args.fail:
        return 0

    if internal_broken_targets > 0:
        return 1
    if external_code is not None and external_hard_fail > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

