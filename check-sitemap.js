/**
 * Sitemap 语法与一致性检查（离线）
 *
 * 目标：避免 GSC 因 sitemap.xml 语法/URL 异常报错。
 *
 * Usage:
 *   hugo --minify --gc
 *   node check-sitemap.js
 */

const fs = require('fs');
const path = require('path');

function fail(message) {
  console.error(`❌ ${message}`);
  process.exitCode = 1;
}

function ok(message) {
  console.log(`✅ ${message}`);
}

function readBaseURL() {
  const configPath = path.join(process.cwd(), 'hugo.toml');
  const raw = fs.readFileSync(configPath, 'utf8');

  const match = raw.match(/^\s*baseURL\s*=\s*"(.*?)"\s*$/m);
  if (!match) return null;

  const baseURL = match[1].trim();
  if (!baseURL) return null;
  return baseURL.endsWith('/') ? baseURL : `${baseURL}/`;
}

function main() {
  const sitemapPath = path.join(process.cwd(), 'public', 'sitemap.xml');
  if (!fs.existsSync(sitemapPath)) {
    fail('未找到 public/sitemap.xml（请先运行 hugo 构建）');
    return;
  }

  const xml = fs.readFileSync(sitemapPath, 'utf8');

  if (!xml.startsWith('<?xml')) {
    fail('sitemap.xml 开头不是 <?xml（可能发生了 XML 转义或输出异常）');
  } else {
    ok('sitemap.xml XML 声明正常');
  }

  if (!xml.includes('<urlset')) fail('sitemap.xml 缺少 <urlset> 根节点');
  if (!xml.includes('http://www.sitemaps.org/schemas/sitemap/0.9')) {
    fail('sitemap.xml 缺少 sitemap 协议命名空间（xmlns）');
  }

  const baseURL = readBaseURL();
  if (!baseURL) {
    fail('无法从 hugo.toml 解析 baseURL（请确保 baseURL 形如 baseURL = \"https://example.com/\"）');
  } else {
    ok(`baseURL: ${baseURL}`);
  }

  const locRegex = /<loc>(.*?)<\/loc>/g;
  const locs = [];
  let match;
  while ((match = locRegex.exec(xml)) !== null) {
    locs.push(match[1].trim());
  }

  if (locs.length === 0) {
    fail('sitemap.xml 未包含任何 <loc> 条目');
    return;
  }

  const seen = new Set();
  const duplicates = [];
  const badPrefix = [];
  const badWhitespace = [];
  const suspicious = [];

  for (const loc of locs) {
    if (seen.has(loc)) duplicates.push(loc);
    seen.add(loc);

    if (/\s/.test(loc)) badWhitespace.push(loc);
    if (baseURL && !loc.startsWith(baseURL)) badPrefix.push(loc);

    if (loc.includes('/page/') || loc.includes('/p/')) suspicious.push(loc);
  }

  if (duplicates.length) {
    fail(`发现重复 <loc>：${duplicates.length} 条（示例：${duplicates[0]}）`);
  } else {
    ok(`未发现重复 <loc>（总计 ${locs.length} 条）`);
  }

  if (badWhitespace.length) {
    fail(`发现包含空白字符的 <loc>：${badWhitespace.length} 条（示例：${badWhitespace[0]}）`);
  } else {
    ok('未发现包含空白字符的 <loc>');
  }

  if (badPrefix.length) {
    fail(`发现与 baseURL 不一致的 <loc>：${badPrefix.length} 条（示例：${badPrefix[0]}）`);
  } else {
    ok('所有 <loc> 与 baseURL 前缀一致');
  }

  if (suspicious.length) {
    fail(`发现疑似分页/非规范路径（/page/ 或 /p/）：${suspicious.length} 条（示例：${suspicious[0]}）`);
  } else {
    ok('未发现疑似分页/非规范路径（/page/ 或 /p/）');
  }

  if (process.exitCode === 1) {
    console.error('\n⚠️  Sitemap 检查失败：请修复后重新构建并复查');
  } else {
    console.log('\n🎉 Sitemap 检查通过');
  }
}

main();

