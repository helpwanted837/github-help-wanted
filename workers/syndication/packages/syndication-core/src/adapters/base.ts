/**
 * 从 RSS 解析得到的文章结构。
 */
export interface Article {
  /** 标题 */
  title: string;
  /** 原文永久链接（canonical） */
  url: string;
  /** Markdown 正文（来自 RSS 的 content:encoded） */
  content: string;
  /** 摘要（纯文本，通常来自 RSS description） */
  excerpt?: string;
  /** 文章发布日期 */
  date: Date;
  /** 可选：标签 */
  tags?: string[];
}

/**
 * 平台配置（从 KV 读取）。
 * 注意：敏感凭据建议通过 Worker Secret 注入后再写入 credentials。
 */
export interface PlatformConfig {
  /** 是否启用该平台 */
  enabled: boolean;
  /** API Key、Token 等（键值由适配器自定义） */
  credentials: Record<string, string>;
  /** 平台特定选项（例如模板、开关等） */
  options?: Record<string, unknown>;
}

/**
 * 发布结果。
 */
export interface PublishResult {
  /** 是否成功 */
  success: boolean;
  /** 发布后的链接（用于外链追踪） */
  url?: string;
  /** 失败原因 */
  error?: string;
  /** 是否属于可重试错误（例如 429 限流） */
  retryable?: boolean;
}

/**
 * 平台适配器接口（可插拔）。
 */
export interface PlatformAdapter {
  /** 适配器内部标识，如 "telegram" / "devto" */
  readonly name: string;
  /** 展示名，如 "Telegram" */
  readonly displayName: string;
  /** 支持的内容类型 */
  readonly contentType: "text" | "image";

  /**
   * 发布文章到目标平台。
   */
  publish(article: Article, config: PlatformConfig): Promise<PublishResult>;

  /**
   * 可选：将 Article 转换为平台需要的格式（Markdown/纯文本/HTML 等）。
   */
  transformContent?(article: Article, config: PlatformConfig): string;

  /**
   * 可选：健康检查（例如验证 token 是否可用）。
   */
  healthCheck?(config: PlatformConfig): Promise<boolean>;
}

