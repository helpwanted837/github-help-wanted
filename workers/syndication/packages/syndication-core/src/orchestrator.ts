import type { Article, PlatformConfig } from "./adapters/base.js";
import { getAdapter } from "./adapters/registry.js";
import { parseRSS, type RSSParseOptions } from "./rss.js";

export interface SiteConfig {
  /** 站点标识 */
  site: string;
  /** RSS 地址 */
  rssUrl: string;
  /** 启用的平台列表 */
  enabledPlatforms: string[];
  /** 平台配置 */
  platformConfigs: Record<string, PlatformConfig>;
  /** 状态上报地址（可选） */
  reportEndpoint?: string;
  /** RSS 解析选项（可选） */
  rssOptions?: RSSParseOptions;
  /**
   * 当 STATE 不存在或找不到 lastProcessedUrl 时，最多处理多少篇（默认 1，避免首次运行刷屏）
   */
  bootstrapMaxItems?: number;
}

export interface ExecutionResult {
  site: string;
  /** ISO 时间字符串（便于序列化与存储） */
  timestamp: string;
  articlesProcessed: number;
  results: ArticleResult[];
}

export interface ArticleResult {
  article: { title: string; url: string };
  platforms: Array<{
    name: string;
    success: boolean;
    url?: string;
    error?: string;
    retryable?: boolean;
  }>;
}

function filterNewArticles(
  articles: Article[],
  lastProcessedUrl: string | undefined,
  bootstrapMaxItems: number
): Article[] {
  if (articles.length === 0) return [];

  // RSS 通常是“最新在前”。为了避免首次运行刷屏，默认只处理 1 篇。
  if (!lastProcessedUrl) {
    return articles.slice(0, Math.max(1, bootstrapMaxItems)).slice().reverse();
  }

  const index = articles.findIndex((a) => a.url === lastProcessedUrl);
  if (index === -1) {
    return articles.slice(0, Math.max(1, bootstrapMaxItems)).slice().reverse();
  }

  // 取 lastProcessedUrl 之前（即更新的文章），并按“旧 -> 新”处理，保证状态更新为最新一篇
  return articles.slice(0, index).slice().reverse();
}

export async function runSyndication(
  config: SiteConfig,
  lastProcessedUrl?: string
): Promise<ExecutionResult> {
  const articles = await parseRSS(config.rssUrl, config.rssOptions);

  const newArticles = filterNewArticles(
    articles,
    lastProcessedUrl,
    config.bootstrapMaxItems ?? 1
  );

  const results: ArticleResult[] = [];

  for (const article of newArticles) {
    const platformResults: ArticleResult["platforms"] = [];

    for (const platformName of config.enabledPlatforms) {
      const adapter = getAdapter(platformName);
      if (!adapter) {
        platformResults.push({
          name: platformName,
          success: false,
          error: `找不到适配器: ${platformName}`
        });
        continue;
      }

      const platformConfig = config.platformConfigs[platformName];
      if (!platformConfig?.enabled) continue;

      try {
        const result = await adapter.publish(article, platformConfig);
        platformResults.push({
          name: platformName,
          success: result.success,
          url: result.url,
          error: result.error,
          retryable: result.retryable
        });
      } catch (err) {
        platformResults.push({
          name: platformName,
          success: false,
          error: err instanceof Error ? err.message : String(err)
        });
      }
    }

    results.push({
      article: { title: article.title, url: article.url },
      platforms: platformResults
    });
  }

  return {
    site: config.site,
    timestamp: new Date().toISOString(),
    articlesProcessed: newArticles.length,
    results
  };
}
