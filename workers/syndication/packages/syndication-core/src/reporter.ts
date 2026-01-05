import type { ExecutionResult } from "./orchestrator.js";

export async function reportResult(
  endpoint: string,
  result: ExecutionResult,
  apiKey: string
): Promise<void> {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`
    },
    body: JSON.stringify(result)
  });

  if (!response.ok) {
    const error = await response.text().catch(() => `HTTP ${response.status}`);
    throw new Error(`上报失败: ${error}`);
  }
}
