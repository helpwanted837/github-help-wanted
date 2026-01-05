import type { ExecutionResult } from "syndication-core";

export interface Env {
  DB: D1Database;

  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_ALERT_CHAT_ID: string;

  RESEND_API_KEY: string;
  RESEND_FROM: string;
  RESEND_TO: string;

  REPORT_API_KEY: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/api/report" && request.method === "POST") {
      const authHeader = request.headers.get("Authorization");
      if (authHeader !== `Bearer ${env.REPORT_API_KEY}`) {
        return new Response("Unauthorized", { status: 401 });
      }

      let result: ExecutionResult;
      try {
        result = (await request.json()) as ExecutionResult;
      } catch {
        return new Response("Bad Request", { status: 400 });
      }

      let executionId: number;
      try {
        executionId = await saveExecution(env.DB, result);
      } catch (error) {
        console.error("写入 D1 失败", error);
        return new Response("Internal Server Error", { status: 500 });
      }

      const failures = extractFailures(result);
      if (failures.length > 0) {
        try {
          await sendTelegramAlert(env, result.site, failures, executionId);
        } catch (error) {
          console.error("Telegram 告警发送失败", error);
        }
      }

      return new Response("OK");
    }

    return new Response("Status Collector", { status: 200 });
  },

  async scheduled(_event: ScheduledEvent, env: Env) {
    let summary: DailySummary | null = null;
    try {
      summary = await getDailySummary(env.DB);
    } catch (error) {
      console.error("查询日汇总失败", error);
    }
    if (!summary) return;

    try {
      await sendResendEmail(env, summary);
    } catch (error) {
      console.error("Resend 汇总邮件发送失败", error);
    }
  }
};

type Failure = {
  platform: string;
  articleUrl: string;
  articleTitle: string;
  error: string;
};

function extractFailures(result: ExecutionResult): Failure[] {
  const failures: Failure[] = [];
  for (const item of result.results ?? []) {
    const articleUrl = item.article?.url ?? "";
    const articleTitle = item.article?.title ?? "";
    for (const platform of item.platforms ?? []) {
      if (platform.success) continue;
      failures.push({
        platform: platform.name,
        articleUrl,
        articleTitle,
        error: platform.error ?? "未知错误"
      });
    }
  }
  return failures;
}

async function saveExecution(db: D1Database, result: ExecutionResult): Promise<number> {
  const counts = countPlatformResults(result);

  const site = String(result.site ?? "");
  const timestamp = String((result as any).timestamp ?? new Date().toISOString());
  const articlesProcessed = Number(result.articlesProcessed ?? 0);

  const insertExecution = await db
    .prepare(
      "INSERT INTO executions (site, timestamp, articles_processed, success_count, failure_count) VALUES (?1, ?2, ?3, ?4, ?5)"
    )
    .bind(site, timestamp, articlesProcessed, counts.success, counts.failure)
    .run();

  const executionId = Number(insertExecution.meta.last_row_id ?? 0);

  const statements: D1PreparedStatement[] = [];
  for (const item of result.results ?? []) {
    for (const platform of item.platforms ?? []) {
      statements.push(
        db
          .prepare(
            "INSERT INTO platform_results (execution_id, article_url, article_title, platform, success, result_url, error) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)"
          )
          .bind(
            executionId,
            String(item.article?.url ?? ""),
            String(item.article?.title ?? ""),
            String(platform.name ?? ""),
            platform.success ? 1 : 0,
            platform.url ? String(platform.url) : null,
            platform.error ? String(platform.error) : null
          )
      );
    }
  }

  if (statements.length > 0) {
    await db.batch(statements);
  }

  return executionId;
}

function countPlatformResults(result: ExecutionResult): { success: number; failure: number } {
  let success = 0;
  let failure = 0;

  for (const item of result.results ?? []) {
    for (const platform of item.platforms ?? []) {
      if (platform.success) success += 1;
      else failure += 1;
    }
  }

  return { success, failure };
}

async function sendTelegramAlert(
  env: Env,
  site: string,
  failures: Failure[],
  executionId: number
): Promise<void> {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_ALERT_CHAT_ID) return;

  const lines: string[] = [];
  lines.push("*分发失败告警*");
  lines.push(`站点: ${site}`);
  lines.push(`执行ID: ${executionId}`);
  lines.push("");
  for (const f of failures.slice(0, 20)) {
    const title = f.articleTitle ? ` - ${f.articleTitle}` : "";
    lines.push(`• ${f.platform}${title}`);
    lines.push(`  ${f.articleUrl}`);
    lines.push(`  ${f.error}`);
  }
  if (failures.length > 20) {
    lines.push("");
    lines.push(`... 还有 ${failures.length - 20} 条失败未展示`);
  }

  const response = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: env.TELEGRAM_ALERT_CHAT_ID,
        text: lines.join("\n"),
        parse_mode: "Markdown",
        disable_web_page_preview: true
      })
    }
  );

  if (!response.ok) {
    const error = await response.text().catch(() => `HTTP ${response.status}`);
    throw new Error(error);
  }
}

type DailySummary = {
  fromIso: string;
  toIso: string;
  bySite: Array<{
    site: string;
    executions: number;
    articles: number;
    success: number;
    failure: number;
  }>;
  topFailures: Array<{
    platform: string;
    failureCount: number;
  }>;
};

async function getDailySummary(db: D1Database): Promise<DailySummary | null> {
  const to = new Date();
  const from = new Date(to.getTime() - 24 * 60 * 60 * 1000);

  const fromIso = from.toISOString();
  const toIso = to.toISOString();

  const bySiteQuery = await db
    .prepare(
      "SELECT site, COUNT(*) AS executions, SUM(articles_processed) AS articles, SUM(success_count) AS success, SUM(failure_count) AS failure FROM executions WHERE timestamp >= ?1 AND timestamp <= ?2 GROUP BY site ORDER BY failure DESC"
    )
    .bind(fromIso, toIso)
    .all();

  const bySite = (bySiteQuery.results ?? []).map((row: any) => ({
    site: String(row.site),
    executions: Number(row.executions ?? 0),
    articles: Number(row.articles ?? 0),
    success: Number(row.success ?? 0),
    failure: Number(row.failure ?? 0)
  }));

  const topFailuresQuery = await db
    .prepare(
      "SELECT platform, COUNT(*) AS failureCount FROM platform_results WHERE success = 0 AND created_at >= datetime('now', '-1 day') GROUP BY platform ORDER BY failureCount DESC LIMIT 10"
    )
    .all();

  const topFailures = (topFailuresQuery.results ?? []).map((row: any) => ({
    platform: String(row.platform),
    failureCount: Number(row.failureCount ?? 0)
  }));

  if (bySite.length === 0 && topFailures.length === 0) return null;
  return { fromIso, toIso, bySite, topFailures };
}

async function sendResendEmail(env: Env, summary: DailySummary): Promise<void> {
  if (!env.RESEND_API_KEY || !env.RESEND_FROM || !env.RESEND_TO) return;

  const date = summary.toIso.slice(0, 10);
  const subject = `Syndication 日汇总 ${date}`;

  const lines: string[] = [];
  lines.push(`统计区间: ${summary.fromIso} ~ ${summary.toIso}`);
  lines.push("");

  if (summary.bySite.length > 0) {
    lines.push("按站点汇总:");
    for (const s of summary.bySite) {
      lines.push(
        `- ${s.site}: 执行 ${s.executions} 次，文章 ${s.articles}，成功 ${s.success}，失败 ${s.failure}`
      );
    }
    lines.push("");
  }

  if (summary.topFailures.length > 0) {
    lines.push("失败平台 Top:");
    for (const f of summary.topFailures) {
      lines.push(`- ${f.platform}: ${f.failureCount}`);
    }
    lines.push("");
  }

  const to = env.RESEND_TO.split(/[\\s,]+/g).map((v) => v.trim()).filter(Boolean);

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      from: env.RESEND_FROM,
      to,
      subject,
      text: lines.join("\n")
    })
  });

  if (!response.ok) {
    const error = await response.text().catch(() => `HTTP ${response.status}`);
    throw new Error(error);
  }
}
