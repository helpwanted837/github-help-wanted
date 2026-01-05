#!/usr/bin/env node
/**
 * Schema.org Validation Script for github-help-wanted
 *
 * Checks:
 * 1. No Microdata (itemscope/itemprop) - should use JSON-LD only
 * 2. No duplicate FAQPage schemas
 * 3. Required fields for common schema types
 * 4. Valid JSON-LD syntax
 *
 * Usage: node validate-schema.js
 */

const fs = require('fs');
const path = require('path');

const PUBLIC_DIR = path.join(__dirname, 'public');

let totalErrors = 0;
let totalWarnings = 0;
let pagesChecked = 0;

function findHtmlFiles(dir) {
  const files = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...findHtmlFiles(fullPath));
    } else if (entry.name.endsWith('.html')) {
      files.push(fullPath);
    }
  }
  return files;
}

function validatePage(filePath) {
  const relativePath = path.relative(PUBLIC_DIR, filePath);
  const content = fs.readFileSync(filePath, 'utf-8');
  const errors = [];
  const warnings = [];

  // Check 1: No Microdata
  if (/itemscope|itemtype|itemprop/.test(content)) {
    errors.push('Contains Microdata (itemscope/itemtype/itemprop) - should use JSON-LD only');
  }

  // Check 2: Extract and validate JSON-LD
  const jsonLdMatches = content.match(/<script type=application\/ld\+json>(.*?)<\/script>/gs) || [];
  const schemaTypes = {};

  for (const match of jsonLdMatches) {
    const jsonStr = match
      .replace(/<script type=application\/ld\+json>/g, '')
      .replace(/<\/script>/g, '')
      .trim();

    try {
      // Handle escaped JSON (Hugo outputs as string)
      let data;
      if (jsonStr.startsWith('"') && jsonStr.endsWith('"')) {
        data = JSON.parse(JSON.parse(jsonStr));
      } else {
        data = JSON.parse(jsonStr);
      }

      const type = data['@type'];
      if (type) {
        schemaTypes[type] = (schemaTypes[type] || 0) + 1;
      }

      // Validate required fields
      if (type === 'FAQPage') {
        if (!data.mainEntity || !Array.isArray(data.mainEntity) || data.mainEntity.length === 0) {
          errors.push('FAQPage missing mainEntity array');
        }
      }

      if (type === 'Article') {
        if (!data.headline) warnings.push('Article missing headline');
        if (!data.datePublished) warnings.push('Article missing datePublished');
        if (!data.author) warnings.push('Article missing author');
      }

      if (type === 'SoftwareApplication') {
        const hasRating = data.aggregateRating && data.aggregateRating.ratingValue;
        const hasOffers = data.offers && data.offers.price !== undefined;
        if (!hasRating && !hasOffers) {
          errors.push('SoftwareApplication requires aggregateRating OR offers');
        }
      }

      if (type === 'Organization') {
        if (!data.name || data.name.trim() === '') {
          errors.push('Organization missing required "name" field');
        }
        if (!data.url) {
          errors.push('Organization missing required "url" field');
        }
      }

    } catch (e) {
      errors.push(`Invalid JSON-LD syntax: ${e.message.substring(0, 50)}`);
    }
  }

  // Check 3: No duplicate schemas
  for (const [type, count] of Object.entries(schemaTypes)) {
    if (count > 1) {
      errors.push(`Duplicate ${type} schema (found ${count})`);
    }
  }

  // Report
  if (errors.length > 0 || warnings.length > 0) {
    console.log(`\n📄 ${relativePath}`);
    for (const error of errors) {
      console.log(`   ❌ ERROR: ${error}`);
      totalErrors++;
    }
    for (const warning of warnings) {
      console.log(`   ⚠️  WARN: ${warning}`);
      totalWarnings++;
    }
  }

  pagesChecked++;
}

// Main
console.log('🔍 Schema.org Validation for github-help-wanted\n');
console.log('Checking:');
console.log('  - No Microdata (itemscope/itemprop)');
console.log('  - No duplicate schemas');
console.log('  - Required fields for FAQPage, Article, SoftwareApplication');
console.log('');

if (!fs.existsSync(PUBLIC_DIR)) {
  console.error('❌ public/ directory not found. Run `hugo --minify` first.');
  process.exit(1);
}

const htmlFiles = findHtmlFiles(PUBLIC_DIR);
for (const file of htmlFiles) {
  validatePage(file);
}

console.log('\n' + '='.repeat(50));
console.log(`📊 Summary: ${pagesChecked} pages checked`);
console.log(`   ❌ Errors: ${totalErrors}`);
console.log(`   ⚠️  Warnings: ${totalWarnings}`);

if (totalErrors > 0) {
  console.log('\n❌ VALIDATION FAILED');
  process.exit(1);
} else {
  console.log('\n✅ VALIDATION PASSED');
  process.exit(0);
}
