# 11 - Issue Finder 工具方案

> 将 Issue Finder 作为站点主打功能，承接原站外链 + pSEO 潜力

---

## 1. 背景与目标

### 1.1 为什么做这个

| 问题 | 解决方案 |
|------|----------|
| DR 从 25 跌到 3.5 | 外链上下文与当前内容不匹配，需要恢复原站核心功能 |
| 外链锚文本分析 | 90% 提到 "Issue 搜索"、"help wanted"、"OSS 贡献入门" |
| 当前站点定位 | 纯内容站，与外链语义不符 |

### 1.2 目标

1. **DR 恢复** - 让外链上下文重新匹配，预期 DR 回升到 15-20
2. **pSEO 落地** - 按语言/标签/项目生成海量页面
3. **真实用户价值** - 不是纯内容农场，是开发者实用工具
4. **商业变现** - Guest Post + Affiliate（开发者工具）

---

## 2. 功能设计

### 2.1 核心功能

复刻原站 `github-help-wanted.com` 的核心体验：

- **Issue 搜索** - 按语言、标签筛选 GitHub 上的 "help wanted" / "good first issue"
- **实时数据** - 调用 GitHub Search API，展示最新 Issue
- **项目信息** - 显示 stars、最近活动、描述

### 2.2 筛选维度

| 维度 | 选项 |
|------|------|
| 语言 | Python, JavaScript, TypeScript, Go, Rust, Java, C++, Ruby, PHP, Swift, Kotlin... |
| 标签 | help wanted, good first issue, bug, documentation, hacktoberfest, easy, beginner... |
| 排序 | 最新创建、最近更新、评论数 |

### 2.3 UI 参考

参考 **goodfirstissue.dev** 的简洁风格：

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Help Wanted                          │
│           Find open source issues and start contributing        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BROWSE BY LANGUAGE          │  ISSUES                         │
│  ┌─────────┐ ┌─────────┐     │  ┌─────────────────────────────┐│
│  │Python×66│ │  JS×47  │     │  │ facebook/react              ││
│  └─────────┘ └─────────┘     │  │ [good first issue] 12 issues││
│  ┌─────────┐ ┌─────────┐     │  │ ⭐ 220k  📅 2 days ago      ││
│  │  TS×44  │ │  Go×43  │     │  └─────────────────────────────┘│
│  └─────────┘ └─────────┘     │  ┌─────────────────────────────┐│
│  ...                         │  │ microsoft/vscode            ││
│                              │  │ [help wanted] 8 issues      ││
│  FILTER BY LABEL             │  │ ⭐ 160k  📅 1 day ago       ││
│  ○ help wanted               │  └─────────────────────────────┘│
│  ○ good first issue          │  ...                            │
│  ○ bug                       │                                 │
│  ○ hacktoberfest             │  [Load More]                    │
│                              │                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. pSEO 策略

### 3.1 URL 结构

```
/                                    # 首页 → Issue Finder 入口
/issues/                             # Issue 列表主页
/issues/python/                      # Python issues
/issues/javascript/                  # JavaScript issues
/issues/python/good-first-issue/     # Python + good first issue
/issues/python/help-wanted/          # Python + help wanted
/issues/hacktoberfest/               # Hacktoberfest issues (季节性)
/projects/{owner}/{repo}/            # 项目专页 (可选，后期)
```

### 3.2 页面生成矩阵

| 语言 (20+) | 标签 (10+) | 组合页面 |
|------------|-----------|---------|
| Python | good-first-issue | /issues/python/good-first-issue/ |
| Python | help-wanted | /issues/python/help-wanted/ |
| JavaScript | good-first-issue | /issues/javascript/good-first-issue/ |
| ... | ... | ... |

**预估页面数**: 20 语言 × 10 标签 = **200+ 落地页**

### 3.3 SEO 价值

每个页面针对一个长尾关键词：
- "python good first issue github"
- "javascript help wanted open source"
- "rust beginner issues"
- "hacktoberfest 2025 issues"

---

## 4. 技术架构

### 4.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Hugo 静态站点                              │
│                                                              │
│  /issues/ (动态交互)        /issues/python/ (SSG + 动态)    │
│  ┌─────────────────────┐    ┌─────────────────────┐         │
│  │ 前端 JS 调用 API     │    │ Hugo 预渲染 + JS 增强│         │
│  └─────────────────────┘    └─────────────────────┘         │
│              │                        │                      │
│              └────────────┬───────────┘                      │
│                           ▼                                  │
│                  fetch('/api/issues')                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Cloudflare Worker (/api/issues)                 │
│                                                              │
│  路由:                                                       │
│  GET /api/issues?language=python&label=help-wanted&page=1    │
│                                                              │
│  逻辑:                                                       │
│  1. 验证参数                                                 │
│  2. 检查缓存 (KV / Cache API)                               │
│  3. 调用 GitHub Search API                                   │
│  4. 缓存结果 (TTL: 10 分钟)                                 │
│  5. 返回 JSON                                                │
│                                                              │
│  限流:                                                       │
│  - GitHub API: 30 requests/min (未认证)                     │
│  - 缓存大幅降低实际请求数                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   GitHub Search API                          │
│                                                              │
│  https://api.github.com/search/issues                        │
│  ?q=is:issue+is:open+label:"help wanted"+language:python     │
│  &sort=created&order=desc&page=1&per_page=30                 │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Worker API 设计

**Endpoint**: `GET /api/issues`

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| language | string | 否 | 编程语言，如 python, javascript |
| label | string | 否 | Issue 标签，如 help-wanted, good-first-issue |
| sort | string | 否 | 排序方式: created, updated, comments |
| order | string | 否 | 排序顺序: desc, asc |
| page | number | 否 | 页码，默认 1 |
| per_page | number | 否 | 每页数量，默认 30，最大 100 |

**响应**:
```json
{
  "total_count": 12345,
  "items": [
    {
      "id": 123456,
      "title": "Add dark mode support",
      "html_url": "https://github.com/owner/repo/issues/123",
      "repository": {
        "full_name": "owner/repo",
        "html_url": "https://github.com/owner/repo",
        "stargazers_count": 5000,
        "description": "A cool project"
      },
      "labels": [
        {"name": "good first issue", "color": "7057ff"}
      ],
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T12:00:00Z",
      "comments": 5
    }
  ],
  "cached": true,
  "cache_age": 120
}
```

### 4.3 缓存策略

| 场景 | TTL | 说明 |
|------|-----|------|
| 热门查询 (Python, JS) | 10 分钟 | 高频访问，保持新鲜 |
| 冷门查询 | 30 分钟 | 低频访问，减少 API 调用 |
| 错误响应 | 1 分钟 | 避免持续失败 |

### 4.4 GitHub API 限制

| 认证方式 | 限制 | 说明 |
|----------|------|------|
| 未认证 | 10 requests/min | 仅用于开发测试 |
| Token 认证 | 30 requests/min | 生产环境使用 |

**建议**: 创建一个 GitHub Personal Access Token (无需任何 scope)，配置到 Worker 环境变量。

---

## 5. 实现步骤

### Phase 1: Worker API (优先)

1. 创建 `workers/issue-finder/` 目录
2. 实现 GitHub API 代理
3. 实现缓存逻辑
4. 部署到 `/api/issues`

### Phase 2: 前端页面

1. 创建 `/issues/` 页面 (Hugo)
2. 实现筛选 UI
3. 实现 Issue 列表渲染
4. 实现分页

### Phase 3: pSEO 页面

1. 创建语言页面模板 `/issues/{language}/`
2. 创建组合页面模板 `/issues/{language}/{label}/`
3. 用 Hugo Data + Template 批量生成
4. 每个页面包含静态内容 + 动态数据区域

### Phase 4: 首页改造

1. 首页突出 Issue Finder 入口
2. 展示热门语言/项目
3. 保留现有内容作为 `/guides/` 子目录

---

## 6. 与现有内容的整合

### 6.1 URL 重构

| 当前 | 改造后 | 说明 |
|------|--------|------|
| / | / | 首页改为 Issue Finder |
| /open-source/ | /guides/open-source/ | 内容移到 guides |
| /devops-engineer/ | /guides/devops/ | 内容移到 guides |
| /issues/ | /issues/ | **新增** Issue Finder |
| /issues/python/ | /issues/python/ | **新增** pSEO 页面 |

### 6.2 内链策略

- Issue Finder 页面链接到相关 Guide 文章
- Guide 文章链接到 Issue Finder ("Find Python issues →")
- 形成内容 + 工具的闭环

---

## 7. 预期收益

### 7.1 SEO

| 指标 | 当前 | 预期 (3个月) |
|------|------|-------------|
| DR | 3.5 | 15-20 |
| 索引页面 | ~50 | 200+ |
| 关键词排名 | 0 | 50+ 长尾词 |

### 7.2 流量

- 目标关键词示例: "python good first issue" (月搜索量 1.3K)
- 预估每个 pSEO 页面带来 10-50 UV/月
- 200 页面 × 30 UV = **6000+ UV/月**

### 7.3 变现

- **Guest Post**: DR 15+ 可定价 $50-100/篇
- **Affiliate**: 推荐 GitHub Copilot、开发者工具等

---

## 8. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| GitHub API 限流 | 缓存 + Token 认证 |
| pSEO 页面质量低 | 每个页面加入独特内容 (语言介绍、贡献指南) |
| 用户体验差 | 参考 goodfirstissue.dev 的简洁设计 |
| 维护成本高 | Worker 无服务器架构，几乎零维护 |

---

## 9. 时间线

| 阶段 | 任务 | 优先级 |
|------|------|--------|
| Week 1 | Worker API 开发 + 部署 | P0 |
| Week 1-2 | 前端页面开发 | P0 |
| Week 2-3 | pSEO 页面批量生成 | P1 |
| Week 3-4 | 首页改造 + 内链优化 | P1 |
| 持续 | 内容优化 + 监控 | P2 |

---

*Last updated: 2025-01-16*
