import type { Article, PlatformAdapter, PlatformConfig, PublishResult } from "./base.js";
import { registerAdapter } from "./registry.js";

function transformContent(article: Article): string {
  const host = new URL(article.url).hostname;
  return `${article.content}\n\n---\n\n*原文发布于 [${host}](${article.url})*`;
}

const devtoAdapter: PlatformAdapter = {
  name: "devto",
  displayName: "Dev.to",
  contentType: "text",

  async publish(article: Article, config: PlatformConfig): Promise<PublishResult> {
    const apiKey = config.credentials.apiKey;
    if (!apiKey) return { success: false, error: "缺少 Dev.to apiKey" };

    const organizationIdRaw = config.credentials.organizationId;
    const organizationId =
      typeof organizationIdRaw === "string" && organizationIdRaw.trim()
        ? Number(organizationIdRaw)
        : undefined;

    const response = await fetch("https://dev.to/api/articles", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-key": apiKey
      },
      body: JSON.stringify({
        article: {
          title: article.title,
          body_markdown: transformContent(article),
          published: true,
          canonical_url: article.url,
          tags: (article.tags ?? []).slice(0, 4),
          organization_id: Number.isFinite(organizationId) ? organizationId : undefined
        }
      })
    });

    if (!response.ok) {
      const error = await response.text().catch(() => `HTTP ${response.status}`);
      return { success: false, error, retryable: response.status === 429 };
    }

    const data: any = await response.json().catch(() => undefined);
    const url = typeof data?.url === "string" ? data.url : undefined;
    return { success: true, url };
  },

  transformContent(article: Article): string {
    return transformContent(article);
  }
};

registerAdapter(devtoAdapter);
export default devtoAdapter;
