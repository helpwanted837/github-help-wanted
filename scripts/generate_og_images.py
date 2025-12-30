#!/usr/bin/env python3
"""
为 github-help-wanted 生成 Open Graph（OG）分享图（1200x630）。

设计目标：
1) 自动化：为 Pillar/Cluster 等页面生成统一风格的分享图
2) 增量：只为“本次 Hugo 会构建的页面”生成（draft!=true 且 date<=now）
3) 稳定：以 slug（或文件名/目录名）作为文件名，避免频繁变化

输出位置：
- static/og/<slug>.jpg
- 状态缓存：.cache/og_images/manifest.json

依赖：
- Pillow（图像生成）
- PyYAML（解析 front matter）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import yaml


try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "缺少依赖 Pillow。请先执行：pip install Pillow\n"
        f"原始错误：{exc}"
    )


CONTENT_DIR = Path("content")
DEFAULT_OUT_DIR = Path("static/og")
DEFAULT_CACHE_DIR = Path(".cache/og_images")
HUGO_CONFIG = Path("hugo.toml")

STYLE_VERSION = "ghw-og-v1"
SITE_DEFAULT_SLUG = "site-default"


@dataclass(frozen=True)
class PageInfo:
    source: Path
    slug: str
    title: str


def _read_site_default_title() -> str:
    if not HUGO_CONFIG.exists():
        return "GitHub Help Wanted"
    try:
        data = tomllib.loads(HUGO_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return "GitHub Help Wanted"

    params = data.get("params") if isinstance(data, dict) else None
    if isinstance(params, dict):
        brand = params.get("brand")
        if isinstance(brand, str) and brand.strip():
            return brand.strip()

    title = data.get("title") if isinstance(data, dict) else None
    if isinstance(title, str) and title.strip():
        return title.strip()

    return "GitHub Help Wanted"


def _read_frontmatter(md_path: Path) -> Dict[str, Any]:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date_type):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            try:
                d = date_type.fromisoformat(s)
                return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
            except ValueError:
                return None
    return None


def _safe_slug(value: str) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")


def _iter_candidate_pages(content_dir: Path) -> Iterable[PageInfo]:
    now = datetime.now(timezone.utc)

    for md in sorted(content_dir.rglob("*.md")):
        # pages/ 下为信任/功能页，不参与自动 OG
        if "pages" in md.parts:
            continue

        fm = _read_frontmatter(md)
        if fm.get("draft") is True:
            continue

        published_at = _parse_datetime(fm.get("date"))
        if published_at is not None:
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            if published_at > now:
                continue

        title = _normalize_spaces(str(fm.get("title") or ""))
        if not title:
            continue

        slug = _normalize_spaces(str(fm.get("slug") or ""))
        if not slug:
            if md.name == "_index.md":
                slug = md.parent.name
            elif md.name == "index.md":
                slug = md.parent.name
            else:
                slug = md.stem
        slug = _safe_slug(slug) or _safe_slug(md.stem)

        yield PageInfo(source=md, slug=slug, title=title)


def _load_font(size: int, bold: bool) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        # Linux (GitHub Actions)
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        # macOS
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf"),
    ]
    for p in candidates:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if not words:
        return []

    lines: list[str] = []
    current = ""
    for w in words:
        candidate = f"{current} {w}".strip()
        width, _ = _measure_text(draw, candidate, font)
        if width <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = w
    if current:
        lines.append(current)
    return lines


def _draw_background(img: Image.Image) -> None:
    # 深色背景 + 紫/青渐变（与站点 UI 风格保持一致）
    base = (13, 17, 23)  # #0d1117
    top = (124, 92, 255)  # #7c5cff
    bottom = (0, 212, 255)  # #00d4ff
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / max(h - 1, 1)
        # 先从 base -> base，再叠加一条彩色渐变带（避免过亮）
        r = int(base[0] * (1 - t) + base[0] * t)
        g = int(base[1] * (1 - t) + base[1] * t)
        b = int(base[2] * (1 - t) + base[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # 斜向彩带（简化实现：两条半透明矩形）
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([(0, 0), (img.width, img.height // 2)], fill=(top[0], top[1], top[2], 45))
    od.rectangle([(0, img.height // 3), (img.width, img.height)], fill=(bottom[0], bottom[1], bottom[2], 35))
    img.alpha_composite(overlay)


def _render_og_image(title: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    base = Image.new("RGBA", (1200, 630), (13, 17, 23, 255))
    _draw_background(base)
    draw = ImageDraw.Draw(base)

    padding_left = 70
    padding_right = 70
    padding_top = 92
    padding_bottom = 132
    max_width = base.width - padding_left - padding_right
    max_height = base.height - padding_top - padding_bottom

    title = _normalize_spaces(title)
    font_size = 74
    line_gap = 14

    while font_size >= 38:
        font = _load_font(font_size, bold=True)
        lines = _wrap_lines(draw, title, font, max_width)
        if not lines:
            break
        if len(lines) > 4:
            font_size -= 4
            continue
        line_h = _measure_text(draw, "Ag", font)[1]
        total_h = len(lines) * line_h + (len(lines) - 1) * line_gap
        if total_h <= max_height:
            break
        font_size -= 4

    font = _load_font(font_size, bold=True)
    lines = _wrap_lines(draw, title, font, max_width)[:4]
    line_h = _measure_text(draw, "Ag", font)[1]
    total_h = len(lines) * line_h + (len(lines) - 1) * line_gap

    y = padding_top + max(0, (max_height - total_h) // 2)
    x = padding_left

    for line in lines:
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font, fill=(240, 242, 248, 255))  # #f0f2f8
        y += line_h + line_gap

    # 品牌标识（文本 logo）
    small = _load_font(26, bold=False)
    brand = "GitHub Help Wanted"
    bw, bh = _measure_text(draw, brand, small)
    draw.text((padding_left, base.height - bh - 48), brand, font=small, fill=(139, 148, 158, 255))  # #8b949e

    rgb = base.convert("RGB")
    rgb.save(out_path, format="JPEG", quality=85, optimize=True, progressive=True)


def _load_manifest(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_manifest(path: Path, manifest: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _signature(title: str) -> str:
    payload = f"{STYLE_VERSION}\n{title}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 github-help-wanted OG 分享图（static/og/*.jpg）")
    parser.add_argument("--content-dir", type=Path, default=CONTENT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--force", action="store_true", help="忽略缓存，全部重新生成")
    args = parser.parse_args()

    manifest_path = args.cache_dir / "manifest.json"
    manifest = {} if args.force else _load_manifest(manifest_path)

    pages = list(_iter_candidate_pages(args.content_dir))
    generated = 0
    skipped = 0

    default_generated = 0
    default_skipped = 0
    default_title = _read_site_default_title()
    default_sig = _signature(default_title)
    default_out = args.out_dir / f"{SITE_DEFAULT_SLUG}.jpg"
    if not args.force and manifest.get(SITE_DEFAULT_SLUG) == default_sig and default_out.exists():
        default_skipped = 1
    else:
        _render_og_image(default_title, default_out)
        manifest[SITE_DEFAULT_SLUG] = default_sig
        default_generated = 1

    for p in pages:
        sig = _signature(p.title)
        out_file = args.out_dir / f"{p.slug}.jpg"
        if not args.force and manifest.get(p.slug) == sig and out_file.exists():
            skipped += 1
            continue
        _render_og_image(p.title, out_file)
        manifest[p.slug] = sig
        generated += 1

    _save_manifest(manifest_path, manifest)
    print(
        "OG images: "
        f"pages={len(pages)} "
        f"generated={generated} "
        f"skipped={skipped} "
        f"site_default_generated={default_generated} "
        f"site_default_skipped={default_skipped} "
        f"out={args.out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
