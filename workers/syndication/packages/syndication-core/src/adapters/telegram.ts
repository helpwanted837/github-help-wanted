import type { Article, PlatformAdapter, PlatformConfig, PublishResult } from "./base.js";
import { registerAdapter } from "./registry.js";

type TelegramParseMode = "Markdown" | "MarkdownV2" | "HTML";

function buildMessage(article: Article, config: PlatformConfig): string {
  const template =
    (config.options?.messageTemplate as string | undefined) ??
    "*{title}*\n\n{excerpt}\n\n[阅读全文]({url})";

  return template
    .replaceAll("{title}", article.title)
    .replaceAll("{excerpt}", article.excerpt ?? "")
    .replaceAll("{url}", article.url)
    .replaceAll(
      "{tags}",
      (article.tags ?? []).map((tag) => `#${tag}`).join(" ")
    );
}

function buildMessageUrl(channelId: string, messageId: number): string | undefined {
  if (channelId.startsWith("@")) {
    const username = channelId.slice(1);
    return `https://t.me/s/${username}/${messageId}`;
  }
  if (channelId.startsWith("-100")) {
    return `https://t.me/c/${channelId.slice(4)}/${messageId}`;
  }
  return undefined;
}

async function safeJson(response: Response): Promise<any> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

const telegramAdapter: PlatformAdapter = {
  name: "telegram",
  displayName: "Telegram",
  contentType: "text",

  async publish(article: Article, config: PlatformConfig): Promise<PublishResult> {
    const botToken = config.credentials.botToken;
    const channelId = config.credentials.channelId;
    if (!botToken) return { success: false, error: "缺少 Telegram botToken" };
    if (!channelId) return { success: false, error: "缺少 Telegram channelId" };

    const message = buildMessage(article, config);
    const parseMode = config.options?.parseMode as TelegramParseMode | undefined;
    const disableWebPagePreview = Boolean(
      (config.options?.disableWebPagePreview as boolean | undefined) ?? false
    );

    const payload: Record<string, unknown> = {
      chat_id: channelId,
      text: message,
      disable_web_page_preview: disableWebPagePreview
    };
    if (parseMode) {
      payload.parse_mode = parseMode;
    }

    const response = await fetch(
      `https://api.telegram.org/bot${botToken}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }
    );

    const data = await safeJson(response);
    if (!response.ok || !data?.ok) {
      const description =
        typeof data?.description === "string"
          ? data.description
          : `HTTP ${response.status}`;
      return { success: false, error: description, retryable: response.status === 429 };
    }

    const messageId: number | undefined = data?.result?.message_id;
    const url = typeof messageId === "number" ? buildMessageUrl(channelId, messageId) : undefined;
    return { success: true, url };
  },

  transformContent(article: Article, config: PlatformConfig): string {
    return buildMessage(article, config);
  }
};

registerAdapter(telegramAdapter);
export default telegramAdapter;
