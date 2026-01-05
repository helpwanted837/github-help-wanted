import type { Article, PlatformAdapter, PlatformConfig, PublishResult } from "./base.js";
import { registerAdapter } from "./registry.js";

function normalizeBlogName(blogName: string): string {
  const trimmed = blogName.trim();
  if (!trimmed) return trimmed;
  if (trimmed.endsWith(".tumblr.com")) return trimmed.slice(0, -".tumblr.com".length);
  return trimmed;
}

const tumblrAdapter: PlatformAdapter = {
  name: "tumblr",
  displayName: "Tumblr",
  contentType: "text",

  async publish(article: Article, config: PlatformConfig): Promise<PublishResult> {
    const accessToken = config.credentials.accessToken;
    const blogNameRaw = config.credentials.blogName;
    if (!accessToken) return { success: false, error: "缺少 Tumblr accessToken" };
    if (!blogNameRaw) return { success: false, error: "缺少 Tumblr blogName" };

    const blogName = normalizeBlogName(blogNameRaw);
    const response = await fetch(`https://api.tumblr.com/v2/blog/${blogName}/posts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`
      },
      body: JSON.stringify({
        type: "text",
        state: "published",
        title: article.title,
        body: article.content,
        tags: (article.tags ?? []).join(","),
        source_url: article.url
      })
    });

    if (!response.ok) {
      const error = await response.text().catch(() => `HTTP ${response.status}`);
      if (response.status === 401) {
        return { success: false, error: "Tumblr token 已失效（401）", retryable: false };
      }
      return { success: false, error, retryable: response.status === 429 };
    }

    const data: any = await response.json().catch(() => undefined);
    const postId = data?.response?.id_string;
    const url = typeof postId === "string" ? `https://${blogName}.tumblr.com/post/${postId}` : undefined;
    return { success: true, url };
  }
};

registerAdapter(tumblrAdapter);
export default tumblrAdapter;
