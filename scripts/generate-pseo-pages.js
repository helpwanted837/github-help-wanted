#!/usr/bin/env node

/**
 * Generate pSEO pages for Issue Finder
 * Creates /issues/{language}/ and /issues/{language}/{label}/ pages
 */

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const ROOT = path.join(__dirname, '..');
const CONTENT_DIR = path.join(ROOT, 'content', 'issues');
const DATA_DIR = path.join(ROOT, 'data');

// Load data files
const languages = yaml.load(fs.readFileSync(path.join(DATA_DIR, 'languages.yaml'), 'utf8'));
const labels = yaml.load(fs.readFileSync(path.join(DATA_DIR, 'issue_labels.yaml'), 'utf8'));

console.log(`Generating pSEO pages for ${languages.length} languages and ${labels.length} labels...`);

// Ensure content/issues directory exists
if (!fs.existsSync(CONTENT_DIR)) {
  fs.mkdirSync(CONTENT_DIR, { recursive: true });
}

let pageCount = 0;

// Generate language pages: /issues/{language}/
for (const lang of languages) {
  const langDir = path.join(CONTENT_DIR, lang.slug);

  if (!fs.existsSync(langDir)) {
    fs.mkdirSync(langDir, { recursive: true });
  }

  const frontmatter = `---
title: "${lang.name} Open Source Issues - Good First Issue & Help Wanted"
description: "Find ${lang.name} open source issues labeled good first issue and help wanted. Start contributing to ${lang.name} projects today."
keywords:
  - ${lang.slug} good first issue
  - ${lang.slug} help wanted
  - ${lang.slug} open source
  - ${lang.slug} contribution
  - ${lang.slug} beginner issues
language: ${lang.slug}
layout: language
noArticleSchema: true
---
`;

  fs.writeFileSync(path.join(langDir, '_index.md'), frontmatter);
  pageCount++;

  // Generate label pages: /issues/{language}/{label}/
  for (const label of labels) {
    const labelDir = path.join(langDir, label.slug);

    if (!fs.existsSync(labelDir)) {
      fs.mkdirSync(labelDir, { recursive: true });
    }

    const labelFrontmatter = `---
title: "${lang.name} ${label.name} Issues - GitHub Open Source"
description: "Find ${lang.name} issues with ${label.name.toLowerCase()} label on GitHub. ${label.description}"
keywords:
  - ${lang.slug} ${label.slug}
  - ${lang.slug} ${label.name.toLowerCase()}
  - ${lang.slug} open source issues
  - github ${lang.slug} ${label.slug}
language: ${lang.slug}
label: ${label.slug}
github_label: "${label.github_label}"
layout: language-label
noArticleSchema: true
---
`;

    fs.writeFileSync(path.join(labelDir, '_index.md'), labelFrontmatter);
    pageCount++;
  }
}

console.log(`Generated ${pageCount} pSEO pages.`);
console.log(`  - ${languages.length} language pages`);
console.log(`  - ${languages.length * labels.length} language+label pages`);
