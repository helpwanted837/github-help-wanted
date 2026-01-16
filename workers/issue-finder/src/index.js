/**
 * Issue Finder API Worker
 *
 * Proxies GitHub Search API with caching to find "help wanted" / "good first issue" issues.
 *
 * GET /api/issues?language=python&label=help-wanted&sort=created&order=desc&page=1&per_page=30
 */

// Allowed parameters
const ALLOWED_LANGUAGES = [
  'python', 'javascript', 'typescript', 'go', 'rust', 'java', 'c++', 'c',
  'ruby', 'php', 'swift', 'kotlin', 'scala', 'haskell', 'elixir', 'clojure',
  'dart', 'lua', 'r', 'julia', 'perl', 'shell', 'powershell', 'vim script'
];

const ALLOWED_LABELS = [
  'help wanted', 'good first issue', 'bug', 'documentation', 'enhancement',
  'hacktoberfest', 'easy', 'beginner', 'beginner-friendly', 'first-timers-only',
  'up-for-grabs', 'contributions welcome', 'starter'
];

const HOT_QUERIES = ['python', 'javascript', 'typescript', 'go', 'rust', 'java'];

// CORS headers
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env, ctx) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    if (request.method !== 'GET') {
      return jsonResponse({ error: 'Method not allowed' }, 405);
    }

    const url = new URL(request.url);

    try {
      const params = parseParams(url.searchParams);
      const cacheKey = buildCacheKey(params);

      // Check cache first
      const cache = caches.default;
      const cachedResponse = await cache.match(cacheKey);

      if (cachedResponse) {
        const data = await cachedResponse.json();
        data.cached = true;
        data.cache_age = Math.floor((Date.now() - data._cached_at) / 1000);
        delete data._cached_at;
        return jsonResponse(data, 200);
      }

      // Fetch from GitHub API
      const githubData = await fetchGitHubIssues(params, env);

      // Transform response
      const responseData = transformResponse(githubData, params);
      responseData._cached_at = Date.now();

      // Cache the response
      const ttl = getCacheTTL(params, env);
      const responseToCache = new Response(JSON.stringify(responseData), {
        headers: { 'Content-Type': 'application/json' }
      });
      ctx.waitUntil(cache.put(cacheKey, responseToCache.clone(), { expirationTtl: ttl }));

      // Return response (without _cached_at)
      responseData.cached = false;
      delete responseData._cached_at;
      return jsonResponse(responseData, 200);

    } catch (error) {
      console.error('Error:', error);

      if (error.status) {
        return jsonResponse({ error: error.message }, error.status);
      }

      return jsonResponse({ error: 'Internal server error' }, 500);
    }
  }
};

function parseParams(searchParams) {
  const language = (searchParams.get('language') || '').toLowerCase().trim();
  const label = (searchParams.get('label') || '').toLowerCase().trim();
  const sort = searchParams.get('sort') || 'created';
  const order = searchParams.get('order') || 'desc';
  const page = Math.max(1, parseInt(searchParams.get('page')) || 1);
  const per_page = Math.min(100, Math.max(1, parseInt(searchParams.get('per_page')) || 30));

  // Validate sort
  if (!['created', 'updated', 'comments'].includes(sort)) {
    throw { status: 400, message: 'Invalid sort parameter' };
  }

  // Validate order
  if (!['asc', 'desc'].includes(order)) {
    throw { status: 400, message: 'Invalid order parameter' };
  }

  return { language, label, sort, order, page, per_page };
}

function buildCacheKey(params) {
  const key = `https://cache.github-help-wanted.com/api/issues?` +
    `language=${params.language}&label=${params.label}&sort=${params.sort}&` +
    `order=${params.order}&page=${params.page}&per_page=${params.per_page}`;
  return new Request(key);
}

async function fetchGitHubIssues(params, env) {
  // Build GitHub Search query
  let query = 'is:issue is:open';

  // Add label filter - default to "help wanted" OR "good first issue" if no label specified
  if (params.label) {
    // Normalize label: "good-first-issue" -> "good first issue"
    const normalizedLabel = params.label.replace(/-/g, ' ');
    query += ` label:"${normalizedLabel}"`;
  } else {
    // Default: search for common contribution labels
    query += ' label:"help wanted","good first issue"';
  }

  // Add language filter
  if (params.language) {
    query += ` language:${params.language}`;
  }

  const githubUrl = new URL('https://api.github.com/search/issues');
  githubUrl.searchParams.set('q', query);
  githubUrl.searchParams.set('sort', params.sort);
  githubUrl.searchParams.set('order', params.order);
  githubUrl.searchParams.set('page', params.page.toString());
  githubUrl.searchParams.set('per_page', params.per_page.toString());

  const headers = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'github-help-wanted.com'
  };

  // Add auth token if available (increases rate limit from 10 to 30 req/min)
  if (env.GITHUB_TOKEN) {
    headers['Authorization'] = `token ${env.GITHUB_TOKEN}`;
  }

  const response = await fetch(githubUrl.toString(), { headers });

  if (!response.ok) {
    const errorBody = await response.text();
    console.error('GitHub API error:', response.status, errorBody);

    if (response.status === 403) {
      throw { status: 429, message: 'Rate limit exceeded. Please try again later.' };
    }
    if (response.status === 422) {
      throw { status: 400, message: 'Invalid search query' };
    }
    throw { status: response.status, message: 'GitHub API error' };
  }

  return response.json();
}

function transformResponse(githubData, params) {
  return {
    total_count: githubData.total_count,
    incomplete_results: githubData.incomplete_results,
    query: {
      language: params.language || null,
      label: params.label || 'help wanted,good first issue',
      sort: params.sort,
      order: params.order,
      page: params.page,
      per_page: params.per_page
    },
    items: (githubData.items || []).map(item => ({
      id: item.id,
      number: item.number,
      title: item.title,
      html_url: item.html_url,
      state: item.state,
      labels: item.labels.map(l => ({
        name: l.name,
        color: l.color
      })),
      comments: item.comments,
      created_at: item.created_at,
      updated_at: item.updated_at,
      // Repository info from URL parsing (GitHub Search API includes repo info in URL)
      repository: parseRepoFromUrl(item.repository_url),
      user: {
        login: item.user.login,
        avatar_url: item.user.avatar_url,
        html_url: item.user.html_url
      }
    }))
  };
}

function parseRepoFromUrl(repoUrl) {
  // https://api.github.com/repos/owner/repo -> { owner, repo, full_name, html_url }
  if (!repoUrl) return null;

  const match = repoUrl.match(/repos\/([^\/]+)\/([^\/]+)/);
  if (!match) return null;

  const owner = match[1];
  const repo = match[2];

  return {
    owner,
    name: repo,
    full_name: `${owner}/${repo}`,
    html_url: `https://github.com/${owner}/${repo}`
  };
}

function getCacheTTL(params, env) {
  const hotTTL = parseInt(env.CACHE_TTL_HOT) || 600;
  const coldTTL = parseInt(env.CACHE_TTL_COLD) || 1800;

  // Hot queries get shorter TTL for freshness
  if (HOT_QUERIES.includes(params.language)) {
    return hotTTL;
  }

  return coldTTL;
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders
    }
  });
}
