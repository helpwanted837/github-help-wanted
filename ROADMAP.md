# GitHub Help Wanted - 开发路线图

## 已完成 ✅

### Phase 1: Issue Finder 基础功能
- [x] Issue Finder API (`/api/issues`) - 代理 GitHub Search API
- [x] Pages Function 实现（解决 Worker Routes 优先级问题）
- [x] pSEO 页面生成：20 语言 × 7 标签 = 140 页面
- [x] Issue 列表页面前端（筛选、分页）

### Phase 1.5: 首页改版
- [x] Header 导航：Issues 主入口 + Languages 下拉 + Guides 下拉
- [x] Footer 重构：5 列布局（Find Issues, Guides, Resources, Legal）
- [x] 首页改版：
  - Hero 区域：清晰价值主张 + CTA
  - 3 个特性卡片（Issue Finder, Contribution Guides, Multiple Languages）
  - Browse by Language：语言网格
  - Browse by Label：Chip 样式
  - Learn to Contribute：Guides 卡片
  - Latest Articles：文章列表

## 待完成 📋

### Phase 2: Topic/领域 pSEO
**目标**: 自动抓取热门 Topics，生成 `/issues/{language}/{topic}/` 页面

**数据来源**:
- 使用 GitHub Search API 搜索 `topic:xxx` 的仓库数量
- 筛选条件：该 topic 下有 ≥100 个仓库且总 stars ≥10k
- 每个语言取 top 20 热门 topics

**技术方案**:
1. 创建 Cloudflare D1 数据库
   - `topics` 表：id, slug, name, repo_count, total_stars
   - `language_topics` 表：language_slug, topic_slug
   - `sync_logs` 表：table_name, synced_at
2. 创建 Cloudflare Worker (Cron) 定期同步热门 topics
3. 导出数据到 Hugo `data/` 目录
4. 创建 Hugo 模板生成 Topic 页面

**预期页面**:
- `/issues/python/machine-learning/`
- `/issues/python/web/`
- `/issues/javascript/react/`
- etc.

### Phase 3: 热门仓库 pSEO
**目标**: 自动抓取热门仓库，生成 `/issues/repo/{owner}/{name}/` 页面

**数据来源**:
- 每个语言取 stars 前 100 的仓库
- 仓库必须有 open issues 且有 help-wanted/good-first-issue 标签

**技术方案**:
1. D1 新增 `repos` 表：id, owner, name, language, stars, open_issues
2. 创建 Cloudflare Worker (Cron) 定期同步热门仓库
3. 导出数据到 Hugo `data/` 目录
4. 创建 Hugo 模板生成仓库页面

**预期页面**:
- `/issues/repo/facebook/react/`
- `/issues/repo/tensorflow/tensorflow/`
- etc.

### Phase 4: 单 Issue 页面（可选）
**状态**: 暂不实现，后续评估 SEO 价值

## 技术栈

- **静态站点**: Hugo
- **托管**: Cloudflare Pages
- **API**: Cloudflare Pages Functions
- **数据库**: Cloudflare D1 (SQLite)
- **对象存储**: Cloudflare R2（可选，用于缓存）
- **定时任务**: Cloudflare Workers Cron Triggers

## D1 数据库 Schema（计划）

```sql
-- Topics 表
CREATE TABLE topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  repo_count INTEGER DEFAULT 0,
  total_stars INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 语言-Topic 关联表
CREATE TABLE language_topics (
  language_slug TEXT NOT NULL,
  topic_slug TEXT NOT NULL,
  repo_count INTEGER DEFAULT 0,
  PRIMARY KEY (language_slug, topic_slug),
  FOREIGN KEY (topic_slug) REFERENCES topics(slug)
);

-- 热门仓库表
CREATE TABLE repos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner TEXT NOT NULL,
  name TEXT NOT NULL,
  full_name TEXT NOT NULL UNIQUE,
  language TEXT,
  stars INTEGER DEFAULT 0,
  open_issues INTEGER DEFAULT 0,
  has_help_wanted BOOLEAN DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 同步日志表
CREATE TABLE sync_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  records_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'success',
  error_message TEXT
);
```

## Worker Cron 计划

| Worker | 触发频率 | 功能 |
|--------|---------|------|
| sync-topics | 每周一次 | 同步各语言热门 Topics |
| sync-repos | 每周一次 | 同步各语言热门仓库 |
| export-data | 每次同步后 | 导出数据到 R2，触发 Hugo 构建 |
