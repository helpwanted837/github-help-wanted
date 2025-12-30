// RSS 健康度监控 Worker（github-help-wanted）
//
// 目标：
// - 每天定时检查 RSS 是否可访问 + 是否看起来像合法 RSS/Atom XML
// - 失败时发送 Telegram 报警（避免分发链路静默失败）
//
// 配置：
// - vars: RSS_URL, SITE_NAME
// - secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_ALERT_CHAT_ID

const DEFAULT_TIMEOUT_MS = 15_000;

function isProbablyXmlRss(text) {
  if (typeof text !== "string") return false;
  const head = text.slice(0, 4096).trimStart().toLowerCase();

  // 明显不是 XML。
  if (!head.startsWith("<?xml") && !head.startsWith("<rss") && !head.startsWith("<feed")) {
    if (head.startsWith("<!doctype html") || head.startsWith("<html")) return false;
  }

  if (head.includes("<rss") || head.includes("<feed")) return true;
  return false;
}

async function fetchWithTimeout(url, init = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort("timeout"), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function sendTelegram(env, text) {
  const token = env.TELEGRAM_BOT_TOKEN;
  const chatId = env.TELEGRAM_ALERT_CHAT_ID;
  if (!token || !chatId) {
    console.log("Telegram 未配置（缺少 TELEGRAM_BOT_TOKEN / TELEGRAM_ALERT_CHAT_ID），跳过报警。");
    return;
  }

  const apiUrl = `https://api.telegram.org/bot${token}/sendMessage`;
  const body = new URLSearchParams();
  body.set("chat_id", chatId);
  body.set("text", text);
  body.set("disable_web_page_preview", "true");

  const resp = await fetch(apiUrl, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: body.toString(),
  });
  if (!resp.ok) {
    const payload = await resp.text().catch(() => "");
    throw new Error(`Telegram 发送失败：HTTP ${resp.status} ${payload}`.slice(0, 500));
  }
}

async function checkRssOnce(env) {
  const rssUrl = env.RSS_URL || "https://github-help-wanted.com/index.xml";
  const siteName = env.SITE_NAME || "github-help-wanted";

  const startedAt = Date.now();
  const resp = await fetchWithTimeout(
    rssUrl,
    {
      method: "GET",
      redirect: "follow",
      headers: {
        "user-agent": "Mozilla/5.0 (compatible; RSSHealthCheck/1.0)",
        accept: "application/xml,text/xml,*/*",
        "cache-control": "no-cache",
      },
    },
    DEFAULT_TIMEOUT_MS,
  );

  const durationMs = Date.now() - startedAt;
  const contentType = resp.headers.get("content-type") || "";

  if (!resp.ok) {
    return {
      ok: false,
      siteName,
      rssUrl,
      status: resp.status,
      contentType,
      durationMs,
      reason: `HTTP ${resp.status}`,
    };
  }

  const text = await resp.text();
  if (!isProbablyXmlRss(text)) {
    const sample = text.slice(0, 300).replace(/\s+/g, " ").trim();
    return {
      ok: false,
      siteName,
      rssUrl,
      status: resp.status,
      contentType,
      durationMs,
      reason: "RSS 内容疑似不是合法 XML（可能是 HTML 错误页/被 WAF 拦截）",
      sample,
    };
  }

  return {
    ok: true,
    siteName,
    rssUrl,
    status: resp.status,
    contentType,
    durationMs,
  };
}

async function runHealthCheck(env) {
  const result = await checkRssOnce(env);
  if (result.ok) {
    console.log("RSS OK", result);
    return;
  }

  const lines = [
    "RSS 健康检查失败",
    `站点：${result.siteName}`,
    `URL：${result.rssUrl}`,
    `状态：${result.status}`,
    `类型：${result.contentType || "-"}`,
    `耗时：${result.durationMs}ms`,
    `原因：${result.reason}`,
  ];
  if (result.sample) lines.push(`样例：${result.sample}`);

  await sendTelegram(env, lines.join("\n"));
  throw new Error(`RSS health check failed: ${result.reason}`);
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(runHealthCheck(env));
  },

  // 方便 wrangler dev / 手动触发调试（无需配置 routes 也不影响 cron 使用）
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return new Response("ok", { status: 200, headers: { "content-type": "text/plain; charset=utf-8" } });
    }
    if (url.pathname === "/trigger") {
      try {
        await runHealthCheck(env);
        return new Response("ok", { status: 200, headers: { "content-type": "text/plain; charset=utf-8" } });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return new Response(msg, { status: 500, headers: { "content-type": "text/plain; charset=utf-8" } });
      }
    }

    ctx.waitUntil(Promise.resolve());
    return new Response("not found", { status: 404 });
  },
};
