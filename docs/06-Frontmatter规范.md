# 06 - Frontmatter 规范（Hugo）

> 目标：统一元数据结构，支持 SEO、内链系统与“定时发布”。

---

## 1. 基本原则

1. 全站统一使用 **YAML frontmatter**（`---` 包裹）。
2. 文章发布时间由 `date` 控制；配合 `hugo.toml` 的 `buildFuture = false` 实现“未来文章不提前上线”。
3. 非文章类页面（关于/隐私/条款等）不展示日期，但仍建议保留 `date` 便于后续审计与更新。
4. 如需自定义 URL（例如把 `content/pages/about.md` 映射为 `/about/`），使用 `url` 字段。

---

## 2. 字段说明（推荐集合）

```yaml
---
title: "DevOps Engineer Salary Guide 2025"
description: "Comprehensive guide to DevOps engineer salaries by location, experience, and skills."
date: 2025-01-15T10:23:45+08:00
draft: false

# SEO
keywords: ["devops engineer salary", "devops salary 2025"]
canonical: ""          # 留空则默认使用页面 permalink
image: ""              # OG 图片（可选）

# 内容关系（用于内链与推荐）
pillar: "/devops-engineer/"  # 上级 Pillar（Cluster 页必填）
related: []                  # 手工指定相关文章（可选，优先于自动推荐）

# 商业标记（运营侧可用）
commercial_value: 4          # 1-5
affiliate_products: ["udemy", "coursera"]
---
```

### 必填字段

- `title`
- `description`
- `date`
- `draft`

### 建议字段

- `keywords`：用于 `<meta name="keywords">`（可选）
- `pillar`：Cluster 页建议必填，Pillar/信任页可省略
- `canonical`：当同一内容存在多个入口时使用
- `commercial_value`、`affiliate_products`：便于后续做变现组件与 A/B

---

## 3. 定时发布（最佳实践）

1. `date` 必须带时区（推荐 `+08:00`），避免 CI 机器时区差异导致提前/延迟发布。
2. 不要把所有文章设置成同一发布时间点；建议随机化到不同分钟/秒（更自然）。
3. 未来日期文章必须 `draft: false` 才能在到期后自动上线（否则永不发布）。

---

## 4. 页面类型建议

- **Pillar（大词）**：`content/<section>/_index.md`
- **Cluster（长尾）**：`content/<section>/<slug>.md`，建议填写 `pillar`
- **信任页**：`content/pages/*.md` + `url: "/xxx/"`

