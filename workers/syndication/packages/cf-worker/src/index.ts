import { runSyndication, type SiteConfig } from "syndication-core";
import { reportResult } from "syndication-core/reporter";

import "syndication-core/adapters/telegram";
import "syndication-core/adapters/devto";
import "syndication-core/adapters/tumblr";
import "syndication-core/adapters/pinterest";

export interface Env {
  CONFIG: KVNamespace;
  STATE: KVNamespace;

  TELEGRAM_BOT_TOKEN: string;
  DEVTO_API_KEY: string;
  TUMBLR_ACCESS_TOKEN: string;
  REPORT_API_KEY: string;
}

export default {
  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil(runOnce(env));
  },

  async fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const url = new URL(request.url);
    if (url.pathname === "/trigger" && request.method === "POST") {
      ctx.waitUntil(runOnce(env));
      return new Response("Triggered");
    }
    if (url.pathname === "/health") {
      return new Response("OK");
    }
    return new Response("Syndication Worker", { status: 200 });
  }
};

async function runOnce(env: Env): Promise<void> {
  const startedAt = Date.now();
  try {
    const configJson = await env.CONFIG.get("settings");
    if (!configJson) {
      console.error("CONFIG/settings 不存在");
      return;
    }

    let config: SiteConfig;
    try {
      config = JSON.parse(configJson) as SiteConfig;
    } catch (error) {
      console.error("CONFIG/settings JSON 解析失败", error);
      return;
    }

    injectSecrets(config, env);

    const lastProcessedUrl = await env.STATE.get("last_processed_url");
    const result = await runSyndication(config, lastProcessedUrl ?? undefined);

    if (result.results.length > 0) {
      const newestUrl = result.results[result.results.length - 1]?.article?.url;
      if (newestUrl) {
        await env.STATE.put("last_processed_url", newestUrl);
      }
    }

    if (config.reportEndpoint) {
      try {
        await reportResult(config.reportEndpoint, result, env.REPORT_API_KEY);
      } catch (error) {
        console.error("上报失败", error);
      }
    }

    console.log(
      `Syndication completed: site=${result.site} articles=${result.articlesProcessed} durationMs=${
        Date.now() - startedAt
      }`
    );
  } catch (error) {
    console.error("Syndication 执行异常", error);
  }
}

function injectSecrets(config: SiteConfig, env: Env): void {
  const telegram = config.platformConfigs?.telegram;
  if (telegram) {
    telegram.credentials.botToken = env.TELEGRAM_BOT_TOKEN;
  }

  const devto = config.platformConfigs?.devto;
  if (devto) {
    devto.credentials.apiKey = env.DEVTO_API_KEY;
  }

  const tumblr = config.platformConfigs?.tumblr;
  if (tumblr) {
    tumblr.credentials.accessToken = env.TUMBLR_ACCESS_TOKEN;
  }
}
