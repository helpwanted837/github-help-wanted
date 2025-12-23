// Umami analytics proxy Worker.
// Route: <site-domain>/a/*
// Mapping:
//   /a/s.js      -> https://umami.hniapi.top/script.js
//   /a/api/send  -> https://umami.hniapi.top/api/send

const DEFAULT_UMAMI_HOST = "umami.hniapi.top";
const PROXY_PREFIX = "/a/";

// Optional: exclude specific client IPs from tracking.
// Configure via Worker secret: EXCLUDED_IPS (comma/whitespace-separated).
function parseExcludedIps(raw) {
  if (typeof raw !== "string" || !raw.trim()) return [];
  return raw
    .split(/[\s,]+/g)
    .map((value) => value.trim())
    .filter(Boolean);
}

function withCors(headers) {
  const newHeaders = new Headers(headers);
  newHeaders.set("Access-Control-Allow-Origin", "*");
  newHeaders.set("Access-Control-Allow-Methods", "GET,HEAD,POST,OPTIONS");
  newHeaders.set(
    "Access-Control-Allow-Headers",
    "Content-Type,User-Agent,Accept,Accept-Language,Referer,Origin,DNT",
  );
  newHeaders.set("Access-Control-Max-Age", "86400");
  return newHeaders;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (!path.startsWith(PROXY_PREFIX)) {
      return fetch(request);
    }

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: withCors() });
    }

    const umamiHost = env?.UMAMI_HOST || DEFAULT_UMAMI_HOST;

    // Exclude specific client IPs (so your own visits never reach Umami).
    const clientIp = request.headers.get("CF-Connecting-IP")?.trim();
    const excludedIps = parseExcludedIps(env?.EXCLUDED_IPS);
    if (clientIp && excludedIps.includes(clientIp)) {
      const headers = withCors();
      headers.set("Cache-Control", "no-store");
      return new Response("", { status: 204, headers });
    }

    // /a/s.js -> /script.js
    // /a/api/send -> /api/send
    let umamiPath = path.replace(PROXY_PREFIX, "/");
    if (umamiPath === "/s.js") {
      umamiPath = "/script.js";
    }

    const targetUrl = new URL(request.url);
    targetUrl.protocol = "https:";
    targetUrl.hostname = umamiHost;
    targetUrl.pathname = umamiPath;

    // Copy headers (avoid forwarding site cookies/auth to Umami).
    const headers = new Headers(request.headers);
    headers.delete("cookie");
    headers.delete("authorization");
    headers.set("host", umamiHost);

    const shouldSendBody = request.method !== "GET" && request.method !== "HEAD";
    const response = await fetch(targetUrl.toString(), {
      method: request.method,
      headers,
      body: shouldSendBody ? request.body : undefined,
      redirect: "manual",
    });

    const newHeaders = withCors(response.headers);
    newHeaders.delete("set-cookie");

    // Cache the script
    if (path.endsWith(".js")) {
      newHeaders.set("Cache-Control", "public, max-age=86400");
    }

    return new Response(response.body, {
      status: response.status,
      headers: newHeaders,
    });
  },
};
