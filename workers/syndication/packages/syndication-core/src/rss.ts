import type { Article } from "./adapters/base.js";
import { decodeXmlEntities, extractCDATA } from "./utils/xml.js";

export interface RSSParseOptions {
  /** 最多处理几篇（默认 10） */
  maxItems?: number;
  /** 只处理此日期之后的 */
  sinceDate?: Date;
}

function escapeForRegex(input: string): string {
  return input.replaceAll(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractTag(itemXml: string, tagName: string): string | undefined {
  const tag = escapeForRegex(tagName);
  const regex = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i");
  const match = itemXml.match(regex);
  return match ? match[1] : undefined;
}

function extractAllTags(itemXml: string, tagName: string): string[] {
  const tag = escapeForRegex(tagName);
  const regex = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "gi");
  return Array.from(itemXml.matchAll(regex)).map((m) => m[1]);
}

/**
 * 仅解析 XML 字符串（便于测试与复用）。
 * 返回的文章顺序与 RSS <item> 顺序一致（通常是“最新在前”）。
 */
export function parseRSSXml(xml: string, options?: RSSParseOptions): Article[] {
  const maxItems = options?.maxItems ?? 10;
  const sinceDate = options?.sinceDate;

  const items = Array.from(xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)).map(
    (m) => m[1]
  );

  const articles: Article[] = [];
  for (const itemXml of items) {
    const titleRaw = extractTag(itemXml, "title") ?? "";
    const linkRaw = extractTag(itemXml, "link") ?? extractTag(itemXml, "guid") ?? "";
    const pubDateRaw = extractTag(itemXml, "pubDate") ?? "";
    const descriptionRaw = extractTag(itemXml, "description") ?? "";
    const contentRaw = extractTag(itemXml, "content:encoded") ?? "";

    const title = decodeXmlEntities(titleRaw).trim();
    const url = decodeXmlEntities(linkRaw).trim();
    const date = new Date(decodeXmlEntities(pubDateRaw).trim());
    const excerpt = decodeXmlEntities(descriptionRaw).trim();
    const content = decodeXmlEntities(extractCDATA(contentRaw)).trim();
    const tags = extractAllTags(itemXml, "category")
      .map((v) => decodeXmlEntities(v).trim())
      .filter(Boolean);

    if (!title || !url || Number.isNaN(date.getTime())) continue;
    if (sinceDate && date.getTime() <= sinceDate.getTime()) continue;

    articles.push({
      title,
      url,
      content,
      excerpt: excerpt || undefined,
      date,
      tags: tags.length > 0 ? tags : undefined
    });

    if (articles.length >= maxItems) break;
  }

  return articles;
}

export async function parseRSS(
  rssUrl: string,
  options?: RSSParseOptions
): Promise<Article[]> {
  const response = await fetch(rssUrl);
  if (!response.ok) {
    throw new Error(`RSS 拉取失败: HTTP ${response.status}`);
  }
  const xml = await response.text();
  return parseRSSXml(xml, options);
}
