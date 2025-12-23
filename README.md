# github-help-wanted.com

> 过期域名复活项目 - 开发者工具/软件领域

---

## 项目状态

- **域名**: github-help-wanted.com
- **当前阶段**: Hugo 站点骨架已完成（模板/SEO/部署脚本）
- **目标**: Day1 13页 → 200页（按 `docs/04-关键词清单.md` 优先级填充）

---

## 快速开始（本地）

```bash
hugo server
```

生成内链数据：

```bash
python3 scripts/generate_internal_links.py --incremental
```

按优先级批量生成占位页面（默认 `draft=true`）：

```bash
python3 scripts/generate_pages_from_keywords.py --priority P1
python3 scripts/generate_pages_from_keywords.py --priority P2
```

## 域名基本面

| 指标 | 数值 | 说明 |
|------|------|------|
| DR | 25 | 中等基础 |
| 外链数 | 200（历史 669） | 有存量 |
| Ref Domains | 183（历史 370） | 分布较广 |
| 高质量来源 | HN(DR91), Qiita(DR87) | 开发者社区认可 |

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [01-域名分析.md](./docs/01-域名分析.md) | 外链分析、必须承接的 URL |
| [02-关键词调研计划.md](./docs/02-关键词调研计划.md) | Ahrefs 调研任务清单 |
| [03-Niche决策.md](./docs/03-Niche决策.md) | 基于调研数据的方向选择（待填充） |
| [04-内容规划.md](./docs/04-内容规划.md) | 300 篇文章的主题结构（待填充） |
| [05-技术实现.md](./docs/05-技术实现.md) | Hugo 站点搭建计划（待填充） |
| [06-Frontmatter规范.md](./docs/06-Frontmatter规范.md) | frontmatter 规范 & 定时发布约定 |

---

## 快速链接

- 策略文档: [../strategy/](../strategy/)
- Hugo PBN 建站手册: [../strategy/Hugo PBN 建站手册.md](../strategy/Hugo%20PBN%20建站手册.md)
- 新站初始化检查清单: [../strategy/新站初始化检查清单.md](../strategy/新站初始化检查清单.md)
- 站点交接文档: [./HANDOFF.md](./HANDOFF.md)

---

*Created: 2025-12-23*
