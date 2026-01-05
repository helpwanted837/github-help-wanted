/**
 * FAQPage 重复标记检查（离线）
 *
 * 目的：避免 “Duplicate field 'FAQPage'” 这类 GSC 报错。
 *
 * 检查：
 * 1) 同页出现多个 JSON-LD FAQPage
 * 2) 同页同时出现 JSON-LD FAQPage + Microdata FAQPage（itemscope/itemtype）
 *
 * Usage:
 *   hugo --minify --gc
 *   node check-duplicate-faqpage.js
 */

const fs = require('fs');
const path = require('path');
const { glob } = require('glob');

function extractJsonLdBlocks(html) {
  const blocks = [];
  const regex = /<script\s+type=["']application\/ld\+json["']\s*>([\s\S]*?)<\/script>/gi;
  let match;
  while ((match = regex.exec(html)) !== null) {
    blocks.push(match[1]);
  }
  return blocks;
}

function isFAQPage(schema) {
  if (!schema) return false;
  const t = schema['@type'];
  if (t === 'FAQPage') return true;
  if (Array.isArray(t) && t.includes('FAQPage')) return true;
  return false;
}

function flattenSchemas(parsed) {
  if (!parsed) return [];
  if (Array.isArray(parsed)) return parsed.flatMap(flattenSchemas);
  if (parsed['@graph'] && Array.isArray(parsed['@graph'])) return parsed['@graph'];
  return [parsed];
}

async function main() {
  const basePath = process.cwd();
  const htmlFiles = await glob('public/**/*.html', { cwd: basePath, absolute: true, ignore: ['**/node_modules/**'] });

  const duplicates = [];
  const mixedFormats = [];

  for (const filePath of htmlFiles) {
    const html = fs.readFileSync(filePath, 'utf8');
    const relPath = path.relative(path.join(basePath, 'public'), filePath).replace(/\\/g, '/');

    const hasMicrodataFAQ = /itemtype=["']https?:\/\/schema\.org\/FAQPage["']/.test(html);
    const jsonldBlocks = extractJsonLdBlocks(html);

    let faqJsonLdCount = 0;
    for (const block of jsonldBlocks) {
      try {
        const parsed = JSON.parse(block);
        const schemas = flattenSchemas(parsed);
        for (const schema of schemas) {
          if (isFAQPage(schema)) faqJsonLdCount += 1;
        }
      } catch {
        // validate-schema.js 已负责 JSON 语法校验，这里不重复报错
      }
    }

    if (faqJsonLdCount > 1) {
      duplicates.push({ path: relPath, count: faqJsonLdCount });
    }
    if (hasMicrodataFAQ && faqJsonLdCount > 0) {
      mixedFormats.push({ path: relPath, count: faqJsonLdCount });
    }
  }

  console.log('\n==================================================');
  console.log('🔎 FAQPage 重复标记检查（public/）');
  console.log('==================================================\n');

  let hasError = false;

  if (duplicates.length) {
    hasError = true;
    console.log(`❌ 发现同页多个 JSON-LD FAQPage：${duplicates.length} 页`);
    duplicates.slice(0, 10).forEach((x, i) => console.log(`${i + 1}. ${x.path} (FAQPage schemas: ${x.count})`));
    if (duplicates.length > 10) console.log(`... 以及 ${duplicates.length - 10} 页`);
    console.log('');
  } else {
    console.log('✅ 未发现同页多个 JSON-LD FAQPage');
  }

  if (mixedFormats.length) {
    hasError = true;
    console.log(`❌ 发现 JSON-LD + Microdata 混用 FAQPage：${mixedFormats.length} 页`);
    mixedFormats.slice(0, 10).forEach((x, i) => console.log(`${i + 1}. ${x.path}`));
    if (mixedFormats.length > 10) console.log(`... 以及 ${mixedFormats.length - 10} 页`);
    console.log('');
  } else {
    console.log('✅ 未发现 JSON-LD + Microdata 混用 FAQPage');
  }

  if (hasError) {
    console.log('⚠️  Exit code 1：请修复模板/内容后重新构建再检查\n');
    process.exit(1);
  }

  console.log('\n🎉 FAQPage 检查通过\n');
}

main();

