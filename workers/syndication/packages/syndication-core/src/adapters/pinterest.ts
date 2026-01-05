import type { Article, PlatformAdapter, PlatformConfig, PublishResult } from "./base.js";
import { registerAdapter } from "./registry.js";

function extractFirstImage(markdown: string): string | undefined {
  const match = markdown.match(/!\[[^\]]*\]\(([^)]+)\)/);
  return match ? match[1] : undefined;
}

const pinterestAdapter: PlatformAdapter = {
  name: "pinterest",
  displayName: "Pinterest",
  contentType: "image",

  async publish(article: Article, config: PlatformConfig): Promise<PublishResult> {
    const webhookUrl = config.credentials.webhookUrl;
    if (!webhookUrl) return { success: false, error: "缺少 Pinterest webhookUrl" };

    const payload = {
      title: article.title,
      url: article.url,
      description: article.excerpt ?? "",
      imageUrl: extractFirstImage(article.content),
      boardId: config.credentials.boardId
    };

    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const error = await response.text().catch(() => `HTTP ${response.status}`);
      return { success: false, error, retryable: response.status === 429 };
    }

    try {
      const data: any = await response.json();
      const url = typeof data?.pin_url === "string" ? data.pin_url : undefined;
      return { success: true, url };
    } catch {
      return { success: true };
    }
  }
};

registerAdapter(pinterestAdapter);
export default pinterestAdapter;
