# GitHub Help Wanted - Syndication Worker

当 `github-help-wanted.com` 发布新文章后，从 RSS 拉取并分发到 Telegram/Telegraph，用于获取外链与曝光。

## 关键约束（PBN）

- 独立部署：此 Worker 应使用 github-help-wanted 对应的 Cloudflare 账号部署（与其他站点隔离）。
- RSS 摘要：RSS `<description>` 优先使用文章 frontmatter `abstract`；否则用正文纯文本截断（保证 Telegram 有足够长的 excerpt）。

## 本地开发

```bash
cd ghw-syndication-worker
pnpm install
pnpm -r build

cd packages/ghw-worker
cp .dev.vars.example .dev.vars
# 编辑 .dev.vars 写入 TELEGRAM_BOT_TOKEN / TELEGRAPH_ACCESS_TOKEN

pnpm exec wrangler dev --local

# 另开终端手动触发
curl -X POST http://localhost:8787/trigger
```

## 配置（Cloudflare KV + Secrets）

### 1) 创建 KV Namespace

需要两个 KV：
- `CONFIG`：存放站点配置（key 固定为 `settings`）
- `STATE`：存放状态（key 固定为 `last_processed_url`，用于去重）

创建后，把两个 Namespace ID 填入：`packages/ghw-worker/wrangler.toml`

### 2) 设置 Secrets

在 `packages/ghw-worker` 目录执行：

```bash
wrangler secret put TELEGRAM_BOT_TOKEN
wrangler secret put TELEGRAPH_ACCESS_TOKEN
```

> 注：如果不提供 `TELEGRAPH_ACCESS_TOKEN`，Telegraph 适配器会尝试自动创建账号并打印 token（不推荐）。

### 3) 写入站点配置到 CONFIG/settings

编辑 `packages/ghw-worker/settings.example.json`，填入 Telegram `channelId` 等信息，然后写入 KV：

```bash
wrangler kv:key put --binding=CONFIG settings --path packages/ghw-worker/settings.example.json
```

## 部署

```bash
cd packages/ghw-worker
pnpm exec wrangler deploy
```
