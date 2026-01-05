import type { Article, PlatformAdapter, PlatformConfig, PublishResult } from "./base.js";
import { registerAdapter } from "./registry.js";

type TelegraphNode = string | { tag: string; attrs?: Record<string, string>; children?: TelegraphNode[] };

// Telegraph 支持的标签
const ALLOWED_TAGS = new Set([
  "a", "aside", "b", "blockquote", "br", "code", "em", "figcaption",
  "figure", "h3", "h4", "hr", "i", "iframe", "img", "li", "ol",
  "p", "pre", "s", "strong", "u", "ul", "video"
]);

// 标签映射（不支持的标签转换为支持的）
const TAG_MAP: Record<string, string> = {
  h1: "h3",
  h2: "h3",
  h5: "h4",
  h6: "h4",
  div: "p",
  section: "p",
  article: "p",
  del: "s",
  strike: "s",
  bold: "b",
  italic: "i",
};

// 需要完全移除的标签（包括内容）
const REMOVE_TAGS = new Set([
  "script", "style", "svg", "noscript", "head", "meta", "link",
  "picture", "source", "canvas", "audio"
]);

// 需要展开的标签（移除标签但保留子内容）
const UNWRAP_TAGS = new Set([
  "span", "main", "header", "footer", "nav", "form", "label",
  "table", "thead", "tbody", "tr", "td", "th", "button", "input"
]);

/**
 * 预处理 HTML：移除自定义组件和复杂结构
 */
function preprocessHtml(html: string): string {
  let cleaned = html;

  // 移除 Mermaid 图表代码块（%%{init...graph...）
  cleaned = cleaned.replace(/%%\{init[\s\S]*?(?:graph|flowchart|sequenceDiagram)[\s\S]*?(?=<\/p>|<\/div>|$)/gi, "");

  // 移除带有 itemscope 的结构化数据块（找到 itemscope 到对应的闭合）
  cleaned = cleaned.replace(/<div[^>]*itemscope[^>]*>[\s\S]*?(?:<\/div>\s*){1,10}(?=<(?:h[1-6]|p|ul|ol|section|article|$))/gi, "");

  // 移除 integration-hero, integration-card 等自定义组件
  cleaned = cleaned.replace(/<div[^>]*integration-[^>]*>[\s\S]*?(?:<\/div>\s*){2,6}/gi, "");

  // 移除 pre 标签中的 Mermaid 代码
  cleaned = cleaned.replace(/<pre[^>]*>[\s\S]*?%%\{[\s\S]*?<\/pre>/gi, "");

  // 移除表格（Telegraph 不支持表格，展开后会很乱）
  cleaned = cleaned.replace(/<table[^>]*>[\s\S]*?<\/table>/gi, "");

  // 多轮清理空的 div 结构
  for (let i = 0; i < 5; i++) {
    const before = cleaned;
    cleaned = cleaned.replace(/<div[^>]*>\s*<\/div>/gi, "");
    cleaned = cleaned.replace(/<div[^>]*>[\s\n]*<\/div>/gi, "");
    if (before === cleaned) break;
  }

  // 清理多余的空行
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");

  return cleaned;
}

/**
 * 简单的 HTML 解析器，将 HTML 字符串转换为 Telegraph Node 格式
 * 基于 Telegraph 官方 API 文档的 domToNode 实现思路
 */
function parseHtmlToNodes(html: string): TelegraphNode[] {
  const nodes: TelegraphNode[] = [];

  // 预处理：移除自定义组件
  let cleaned = preprocessHtml(html);

  // 移除需要完全删除的标签及其内容
  for (const tag of REMOVE_TAGS) {
    const regex = new RegExp(`<${tag}[^>]*>[\\s\\S]*?</${tag}>`, "gi");
    cleaned = cleaned.replace(regex, "");
    // 自闭合标签
    cleaned = cleaned.replace(new RegExp(`<${tag}[^>]*/?>`, "gi"), "");
  }

  // 移除 HTML 注释
  cleaned = cleaned.replace(/<!--[\s\S]*?-->/g, "");

  // 使用栈来解析 HTML
  const result = parseFragment(cleaned);
  return result;
}

/**
 * 解析 HTML 片段，返回 Telegraph 节点数组
 */
function parseFragment(html: string): TelegraphNode[] {
  const nodes: TelegraphNode[] = [];
  let pos = 0;

  while (pos < html.length) {
    // 查找下一个标签
    const tagStart = html.indexOf("<", pos);

    // 处理标签前的文本
    if (tagStart === -1) {
      // 没有更多标签，添加剩余文本
      const text = decodeHtmlEntities(html.slice(pos).trim());
      if (text) nodes.push(text);
      break;
    }

    if (tagStart > pos) {
      // 标签前有文本
      const text = decodeHtmlEntities(html.slice(pos, tagStart).trim());
      if (text) nodes.push(text);
    }

    // 解析标签
    const tagEnd = html.indexOf(">", tagStart);
    if (tagEnd === -1) {
      // 无效标签，跳过
      pos = tagStart + 1;
      continue;
    }

    const tagContent = html.slice(tagStart + 1, tagEnd);

    // 自闭合标签检测
    const isSelfClosing = tagContent.endsWith("/") || /^(br|hr|img|iframe|video)\b/i.test(tagContent);

    // 结束标签检测
    if (tagContent.startsWith("/")) {
      // 这是结束标签，在递归调用中处理
      pos = tagEnd + 1;
      continue;
    }

    // 解析标签名和属性
    const tagMatch = tagContent.match(/^([a-zA-Z][a-zA-Z0-9]*)/);
    if (!tagMatch) {
      pos = tagEnd + 1;
      continue;
    }

    let tagName = tagMatch[1].toLowerCase();
    const originalTag = tagName;

    // 标签映射
    if (TAG_MAP[tagName]) {
      tagName = TAG_MAP[tagName];
    }

    // 跳过需要展开的标签
    if (UNWRAP_TAGS.has(originalTag)) {
      // 找到对应的结束标签，递归处理内部内容
      const closeTag = `</${originalTag}>`;
      const closeIndex = findClosingTag(html, tagEnd + 1, originalTag);
      if (closeIndex !== -1) {
        const innerHtml = html.slice(tagEnd + 1, closeIndex);
        const innerNodes = parseFragment(innerHtml);
        nodes.push(...innerNodes);
        pos = closeIndex + closeTag.length;
      } else {
        pos = tagEnd + 1;
      }
      continue;
    }

    // 检查是否是支持的标签
    if (!ALLOWED_TAGS.has(tagName)) {
      // 不支持的标签，尝试提取内容
      const closeIndex = findClosingTag(html, tagEnd + 1, originalTag);
      if (closeIndex !== -1) {
        const innerHtml = html.slice(tagEnd + 1, closeIndex);
        const innerNodes = parseFragment(innerHtml);
        nodes.push(...innerNodes);
        pos = closeIndex + `</${originalTag}>`.length;
      } else {
        pos = tagEnd + 1;
      }
      continue;
    }

    // 提取属性
    const attrs: Record<string, string> = {};
    const attrRegex = /\b(href|src)=["']([^"']*)["']/gi;
    let attrMatch;
    while ((attrMatch = attrRegex.exec(tagContent)) !== null) {
      attrs[attrMatch[1].toLowerCase()] = attrMatch[2];
    }

    // 创建节点
    const node: TelegraphNode = { tag: tagName };
    if (Object.keys(attrs).length > 0) {
      node.attrs = attrs;
    }

    // 处理自闭合标签
    if (isSelfClosing) {
      nodes.push(node);
      pos = tagEnd + 1;
      continue;
    }

    // 找到结束标签
    const closeIndex = findClosingTag(html, tagEnd + 1, originalTag);
    if (closeIndex !== -1) {
      const innerHtml = html.slice(tagEnd + 1, closeIndex);
      const children = parseFragment(innerHtml);
      if (children.length > 0) {
        node.children = children;
      }
      pos = closeIndex + `</${originalTag}>`.length;
    } else {
      pos = tagEnd + 1;
    }

    nodes.push(node);
  }

  return nodes;
}

/**
 * 查找匹配的结束标签位置
 */
function findClosingTag(html: string, startPos: number, tagName: string): number {
  let depth = 1;
  let pos = startPos;
  const openPattern = new RegExp(`<${tagName}[\\s>]`, "gi");
  const closePattern = new RegExp(`</${tagName}>`, "gi");

  while (pos < html.length && depth > 0) {
    openPattern.lastIndex = pos;
    closePattern.lastIndex = pos;

    const openMatch = openPattern.exec(html);
    const closeMatch = closePattern.exec(html);

    if (!closeMatch) break;

    if (openMatch && openMatch.index < closeMatch.index) {
      depth++;
      pos = openMatch.index + openMatch[0].length;
    } else {
      depth--;
      if (depth === 0) {
        return closeMatch.index;
      }
      pos = closeMatch.index + closeMatch[0].length;
    }
  }

  return -1;
}

/**
 * 解码 HTML 实体
 */
function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&nbsp;/g, " ")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&ldquo;/g, '"')
    .replace(/&rdquo;/g, '"')
    .replace(/&lsquo;/g, "'")
    .replace(/&rsquo;/g, "'")
    .replace(/&mdash;/g, "—")
    .replace(/&ndash;/g, "–")
    .replace(/&rarr;/g, "→")
    .replace(/&larr;/g, "←")
    .replace(/&hellip;/g, "…")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(parseInt(code, 10)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, code) => String.fromCharCode(parseInt(code, 16)));
}

async function safeJson(response: Response): Promise<any> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

const telegraphAdapter: PlatformAdapter = {
  name: "telegraph",
  displayName: "Telegraph",
  contentType: "text",

  async publish(article: Article, config: PlatformConfig): Promise<PublishResult> {
    let accessToken = config.credentials.accessToken;
    const authorName = (config.options?.authorName as string | undefined) ?? "GitHub Help Wanted";
    const authorUrl = (config.options?.authorUrl as string | undefined) ?? article.url;

    // 如果没有 accessToken，先创建账号
    if (!accessToken) {
      const shortName = (config.options?.shortName as string | undefined) ?? "syndication";
      const createAccountResponse = await fetch(
        `https://api.telegra.ph/createAccount?short_name=${encodeURIComponent(shortName)}&author_name=${encodeURIComponent(authorName)}`
      );
      const accountData = await safeJson(createAccountResponse);
      if (!accountData?.ok || !accountData?.result?.access_token) {
        return {
          success: false,
          error: `创建 Telegraph 账号失败: ${accountData?.error ?? "unknown"}`
        };
      }
      accessToken = accountData.result.access_token;
      console.log(`Telegraph: 创建了新账号，token=${accessToken}`);
    }

    // 构建内容节点 - 使用纯文本摘要
    const nodes: TelegraphNode[] = [];

    // 使用 excerpt（纯文本摘要）
    const excerpt = article.excerpt || "";
    if (excerpt) {
      nodes.push({ tag: "p", children: [excerpt] });
    }

    // 添加原文链接
    nodes.push({ tag: "hr" });
    nodes.push({
      tag: "p",
      children: [
        { tag: "strong", children: ["Read full article: "] },
        { tag: "a", attrs: { href: article.url }, children: [article.title] }
      ]
    });

    // 创建页面
    const payload = {
      access_token: accessToken,
      title: article.title,
      author_name: authorName,
      author_url: authorUrl,
      content: JSON.stringify(nodes)
    };

    const response = await fetch("https://api.telegra.ph/createPage", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(payload as Record<string, string>)
    });

    const data = await safeJson(response);
    if (!response.ok || !data?.ok) {
      const errorMsg = data?.error ?? `HTTP ${response.status}`;
      return {
        success: false,
        error: errorMsg,
        retryable: response.status === 429
      };
    }

    return {
      success: true,
      url: data.result?.url
    };
  },

  transformContent(article: Article, _config: PlatformConfig): string {
    return article.content || article.excerpt || "";
  }
};

registerAdapter(telegraphAdapter);
export default telegraphAdapter;
