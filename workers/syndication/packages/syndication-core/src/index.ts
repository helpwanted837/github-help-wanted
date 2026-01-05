export type {
  Article,
  PlatformAdapter,
  PlatformConfig,
  PublishResult
} from "./adapters/base.js";
export {
  getAdapter,
  getAdapterNames,
  getAllAdapters,
  registerAdapter
} from "./adapters/registry.js";
export { parseRSS, type RSSParseOptions } from "./rss.js";
export {
  runSyndication,
  type ArticleResult,
  type ExecutionResult,
  type SiteConfig
} from "./orchestrator.js";
