# HANDOFF - github-help-wanted.com

> 站点交接与上线清单（PBN 策略版）

---

## 1. 站点信息

- 域名：`github-help-wanted.com`
- 生成器：Hugo
- 部署：Cloudflare Pages（通过 GitHub Actions 推送构建产物）
- 自动发布：`buildFuture = false` + 定时工作流

---

## 2. 关键约束（PBN）

1. **一站一账号**：独立 GitHub / Cloudflare 账号（不要复用主账号）。
2. **不接入 GSC**：不放 Google verification；只考虑 Bing/Yandex。
3. **发布节奏**：尽量分散 `date` 与部署时间（工作流内已加入 jitter）。

---

## 3. Cloudflare Pages 配置

### 3.1 Pages 项目

- Project name：`github-help-wanted`
- Build command：由 GitHub Actions 负责（Pages 仅接收上传产物）

### 3.2 GitHub Secrets（仓库级）

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

---

## 4. 历史 URL 承接（关键）

历史外链大量指向 `/?languages=...&labels=...` 形式。

Cloudflare Pages 的 `_redirects` **不支持按 query 参数匹配 source**（官方限制），因此这里采用 Pages Functions：

- 规则实现：`functions/index.ts`
- 目标：
  - `languages=Python` → `/open-source/python/`
  - `languages=JavaScript` → `/open-source/javascript/`
  - `labels=hacktoberfest` → `/open-source/hacktoberfest/`
  - `labels=help+wanted` / `good first issue` → `/open-source/good-first-issue/`

---

## 5. 本地开发（可选）

1. 安装 Hugo（extended）
2. 运行：

```bash
hugo server
```

---

## 6. 内链系统

- 生成脚本：`scripts/generate_internal_links.py`
- 输出文件：`data/internal_links.json`
- 注入位置：前三个 H2 标题后（`layouts/_default/_markup/render-heading.html`）

---

## 7. 内容规范

- Frontmatter 规范：`docs/06-Frontmatter规范.md`
- 模板：`scripts/templates/article.md`

