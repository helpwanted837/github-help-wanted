import { runSyndication, type SiteConfig } from "syndication-core";
import "syndication-core/adapters/telegram";
import "syndication-core/adapters/telegraph";

export interface Env {
  CONFIG: KVNamespace;
  STATE: KVNamespace;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_ALERT_CHAT_ID?: string;
  TELEGRAPH_ACCESS_TOKEN?: string;
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
    return new Response("GitHub Help Wanted Syndication Worker", { status: 200 });
  }
};

async function runOnce(env: Env): Promise<void> {
  const startedAt = Date.now();
  try {
    const configJson = await env.CONFIG.get("settings");
    if (!configJson) {
      await recordFailureAndAlert(env, {
        reason: "CONFIG/settings 不存在",
        startedAt,
      });
      return;
    }

    let config: SiteConfig;
    try {
      config = JSON.parse(configJson) as SiteConfig;
    } catch (error) {
      await recordFailureAndAlert(env, {
        reason: "CONFIG/settings JSON 解析失败",
        startedAt,
        error,
      });
      return;
    }

    // 注入 Bot Token
    const telegram = config.platformConfigs?.telegram;
    if (telegram) {
      telegram.credentials.botToken = env.TELEGRAM_BOT_TOKEN;
    }

    // 可选：注入 Telegraph Token（避免把 token 写进 KV）
    const telegraph = config.platformConfigs?.telegraph;
    if (telegraph && env.TELEGRAPH_ACCESS_TOKEN) {
      telegraph.credentials.accessToken = env.TELEGRAPH_ACCESS_TOKEN;
    }

    const lastProcessedUrl = await env.STATE.get("last_processed_url");
    const result = await runSyndication(config, lastProcessedUrl ?? undefined);

    if (result.results.length > 0) {
      const newestUrl = result.results[result.results.length - 1]?.article?.url;
      if (newestUrl) {
        await env.STATE.put("last_processed_url", newestUrl);
      }
    }

    console.log(
      `Syndication completed: site=${result.site} articles=${result.articlesProcessed} durationMs=${
        Date.now() - startedAt
      }`
    );

    const failures: Array<{
      platform: string;
      title: string;
      url: string;
      error: string;
    }> = [];

    // 打印详细结果
    for (const r of result.results) {
      for (const p of r.platforms) {
        if (p.success) {
          console.log(`✓ ${p.name}: ${r.article.title} -> ${p.url}`);
        } else {
          console.error(`✗ ${p.name}: ${r.article.title} - ${p.error}`);
          failures.push({
            platform: p.name,
            title: r.article.title,
            url: r.article.url,
            error: String(p.error ?? "未知错误"),
          });
        }
      }
    }

    if (failures.length > 0) {
      await recordFailureAndAlert(env, {
        reason: "存在平台发布失败",
        startedAt,
        failures,
      });
      return;
    }

    await env.STATE.put("last_success_at", new Date().toISOString());
    await env.STATE.delete("last_failure");
    await env.STATE.delete("last_failure_signature");
  } catch (error) {
    await recordFailureAndAlert(env, {
      reason: "Syndication 执行异常",
      startedAt,
      error,
    });
  }
}

function normalizeError(error: unknown): string {
  if (error instanceof Error) return error.message || String(error);
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
}

function buildFailureSignature(input: {
  reason: string;
  failures?: Array<{ platform: string; url: string }>;
  error?: unknown;
}): string {
  const parts: string[] = [input.reason];
  if (input.failures?.length) {
    for (const f of input.failures.slice(0, 5)) parts.push(`${f.platform}:${f.url}`);
  } else if (input.error) {
    parts.push(normalizeError(input.error).slice(0, 120));
  }
  return parts.join("|");
}

async function recordFailureAndAlert(
  env: Env,
  input: {
    reason: string;
    startedAt: number;
    failures?: Array<{ platform: string; title: string; url: string; error: string }>;
    error?: unknown;
  }
): Promise<void> {
  const signature = buildFailureSignature({
    reason: input.reason,
    failures: input.failures?.map((f) => ({ platform: f.platform, url: f.url })),
    error: input.error,
  });

  const payload = {
    at: new Date().toISOString(),
    reason: input.reason,
    durationMs: Date.now() - input.startedAt,
    error: input.error ? normalizeError(input.error) : null,
    failures: input.failures?.slice(0, 10) ?? [],
    signature,
  };

  try {
    await env.STATE.put("last_failure", JSON.stringify(payload));
    await env.STATE.put("last_failure_signature", signature);
  } catch (error) {
    console.error("写入 KV 失败", error);
  }

  await maybeAlertTelegram(env, payload);
}

async function maybeAlertTelegram(
  env: Env,
  payload: {
    at: string;
    reason: string;
    durationMs: number;
    error: string | null;
    failures: Array<{ platform: string; title: string; url: string; error: string }>;
    signature: string;
  }
): Promise<void> {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_ALERT_CHAT_ID) return;

  const cooldownMs = 6 * 60 * 60 * 1000;
  try {
    const lastSig = await env.STATE.get("last_alert_signature");
    const lastAtRaw = await env.STATE.get("last_alert_at_ms");
    const lastAt = lastAtRaw ? Number.parseInt(lastAtRaw, 10) : 0;
    const now = Date.now();
    if (lastSig === payload.signature && lastAt && now - lastAt < cooldownMs) {
      console.log("报警去重命中（cooldown 内），跳过 Telegram 发送。");
      return;
    }

    const lines: string[] = [
      "Syndication 发布失败告警",
      "站点：github-help-wanted",
      `时间：${payload.at}`,
      `原因：${payload.reason}`,
      `耗时：${payload.durationMs}ms`,
    ];
    if (payload.error) lines.push(`异常：${payload.error}`);
    for (const f of payload.failures.slice(0, 5)) {
      lines.push(`- ${f.platform}: ${f.title} (${f.url}) -> ${f.error}`.slice(0, 350));
    }
    if (payload.failures.length > 5) lines.push(`… 还有 ${payload.failures.length - 5} 条失败`);

    await sendTelegram(env, lines.join("\n"));

    await env.STATE.put("last_alert_signature", payload.signature);
    await env.STATE.put("last_alert_at_ms", String(now));
  } catch (error) {
    console.error("Telegram 告警发送失败", error);
  }
}

async function sendTelegram(env: Env, text: string): Promise<void> {
  if (!env.TELEGRAM_ALERT_CHAT_ID) return;
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({
      chat_id: env.TELEGRAM_ALERT_CHAT_ID,
      text,
      disable_web_page_preview: true,
    }),
  });

  if (!response.ok) {
    const error = await response.text().catch(() => `HTTP ${response.status}`);
    throw new Error(error);
  }
}
