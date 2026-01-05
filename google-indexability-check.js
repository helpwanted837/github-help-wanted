/**
 * Google Indexability Pre-Deployment Check (github-help-wanted)
 * Simulates Google's indexing validation without network access
 * Checks: Schema validity, robots tags, canonical conflicts, meta tags
 *
 * Usage: node google-indexability-check.js
 */

const fs = require('fs');
const path = require('path');
const { glob } = require('glob');

// Color codes for terminal output
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
};

const c = (color, text) => `${colors[color]}${text}${colors.reset}`;

async function checkGoogleIndexability() {
    console.log('\n' + '='.repeat(80));
    console.log(c('cyan', '🤖 GOOGLE INDEXABILITY PRE-DEPLOYMENT CHECK'));
    console.log('='.repeat(80) + '\n');

    const basePath = process.cwd();
    const htmlFiles = await glob('public/**/*.html', {
        cwd: basePath,
        absolute: true,
        ignore: ['**/node_modules/**']
    });

    console.log(c('blue', `📁 Scanning ${htmlFiles.length} HTML files...\n`));

    // Results tracking
    const results = {
        totalPages: htmlFiles.length,
        schemaErrors: [],
        canonicalConflicts: [],
        noindexPages: [],
        missingMeta: [],
        validPages: 0,
    };

    for (const filePath of htmlFiles) {
        const html = fs.readFileSync(filePath, 'utf-8');
        const relPath = path.relative(path.join(basePath, 'public'), filePath);

        const pageIssues = {
            path: relPath,
            url: relPath.replace(/\\/g, '/').replace(/index\.html$/, ''),
            issues: []
        };

        // 1. Check for incomplete SoftwareApplication schemas
        const schemaRegex = /<script type=application\/ld\+json>(.*?)<\/script>/g;
        let match;
        while ((match = schemaRegex.exec(html)) !== null) {
            try {
                const schema = JSON.parse(match[1]);

                if (schema['@type'] === 'SoftwareApplication') {
                    const hasRating = !!(schema.aggregateRating && schema.aggregateRating.ratingValue);
                    const hasOffers = !!schema.offers;

                    if (!hasRating && !hasOffers) {
                        pageIssues.issues.push({
                            type: 'SCHEMA_ERROR',
                            severity: 'CRITICAL',
                            message: 'Incomplete SoftwareApplication schema (missing rating AND offers)',
                            impact: 'Google will show "2 invalid items detected" error',
                            fix: 'Template fix should remove this schema after rebuild'
                        });
                    }
                }
            } catch (e) {
                // Ignore parse errors
            }
        }

        // 2. Check for canonical + noindex conflict
        const hasCanonical = /<link rel="canonical"/.test(html);
        const hasNoindex = /<meta name="robots" content="[^"]*noindex/.test(html);

        if (hasCanonical && hasNoindex) {
            pageIssues.issues.push({
                type: 'CANONICAL_CONFLICT',
                severity: 'WARNING',
                message: 'Page has both canonical tag and noindex directive',
                impact: 'Conflicting signals to Google (canonical says "index here", noindex says "don\'t index")',
                fix: 'Should remove canonical when noindex is present'
            });
        }

        // 3. Track noindex pages (informational, not an error)
        if (hasNoindex) {
            const robotsMatch = html.match(/<meta name="robots" content="([^"]+)"/);
            results.noindexPages.push({
                path: relPath,
                directive: robotsMatch ? robotsMatch[1] : 'noindex'
            });
        }

        // 4. Check for missing essential meta tags
        const hasTitle = /<title>/.test(html);
        const hasDescription = /<meta name="description"/.test(html) || /<meta property="og:description"/.test(html);

        if (!hasTitle) {
            pageIssues.issues.push({
                type: 'MISSING_META',
                severity: 'CRITICAL',
                message: 'Missing <title> tag',
                impact: 'Page will not index properly without title',
                fix: 'Add title tag in template'
            });
        }

        if (!hasDescription) {
            pageIssues.issues.push({
                type: 'MISSING_META',
                severity: 'WARNING',
                message: 'Missing meta description',
                impact: 'Google may generate poor snippet text',
                fix: 'Add meta description'
            });
        }

        // Categorize results
        if (pageIssues.issues.length > 0) {
            pageIssues.issues.forEach(issue => {
                if (issue.type === 'SCHEMA_ERROR') {
                    results.schemaErrors.push(pageIssues);
                } else if (issue.type === 'CANONICAL_CONFLICT') {
                    results.canonicalConflicts.push(pageIssues);
                } else if (issue.type === 'MISSING_META') {
                    results.missingMeta.push(pageIssues);
                }
            });
        } else if (!hasNoindex) {
            results.validPages++;
        }
    }

    // Remove duplicates
    results.schemaErrors = Array.from(new Set(results.schemaErrors.map(p => p.path)))
        .map(path => results.schemaErrors.find(p => p.path === path));
    results.canonicalConflicts = Array.from(new Set(results.canonicalConflicts.map(p => p.path)))
        .map(path => results.canonicalConflicts.find(p => p.path === path));

    // Print Report
    console.log('='.repeat(80));
    console.log(c('cyan', '📊 INDEXABILITY SUMMARY'));
    console.log('='.repeat(80));
    console.log(`Total pages scanned: ${results.totalPages}`);
    console.log(c('green', `✅ Pages ready for indexing: ${results.validPages}`));
    console.log(c('yellow', `⚠️  Pages with noindex (intentional): ${results.noindexPages.length}`));
    console.log(c('red', `❌ Pages with CRITICAL issues: ${results.schemaErrors.length}`));
    console.log(c('yellow', `⚠️  Pages with warnings: ${results.canonicalConflicts.length + results.missingMeta.length}`));

    // Schema Errors (CRITICAL)
    if (results.schemaErrors.length > 0) {
        console.log('\n' + '='.repeat(80));
        console.log(c('red', '❌ CRITICAL: INCOMPLETE SCHEMA ERRORS (Will Block Indexing)'));
        console.log('='.repeat(80));
        console.log(c('red', `${results.schemaErrors.length} pages have incomplete SoftwareApplication schemas`));
        console.log(c('yellow', '\n⚠️  NOTE: These issues are in the current public/ build'));
        console.log(c('green', '✅ Fix templates/content, rebuild, then re-run this script to verify they are gone\n'));

        console.log('Sample affected pages (first 10):');
        results.schemaErrors.slice(0, 10).forEach((page, i) => {
            console.log(`${i + 1}. ${page.path}`);
            page.issues.forEach(issue => {
                console.log(`   ⚠️  ${issue.message}`);
                console.log(`   📍 Impact: ${issue.impact}`);
            });
        });

        if (results.schemaErrors.length > 10) {
            console.log(`   ... and ${results.schemaErrors.length - 10} more pages`);
        }
    }

    // Canonical Conflicts (WARNING)
    if (results.canonicalConflicts.length > 0) {
        console.log('\n' + '='.repeat(80));
        console.log(c('yellow', '⚠️  WARNING: Canonical + Noindex Conflicts'));
        console.log('='.repeat(80));
        console.log(`${results.canonicalConflicts.length} pages have conflicting directives\n`);

        results.canonicalConflicts.slice(0, 5).forEach((page, i) => {
            console.log(`${i + 1}. ${page.path}`);
            page.issues.forEach(issue => {
                console.log(`   ⚠️  ${issue.message}`);
                console.log(`   📍 Impact: ${issue.impact}`);
            });
        });
    }

    // Noindex Pages (Informational)
    if (results.noindexPages.length > 0) {
        console.log('\n' + '='.repeat(80));
        console.log(c('blue', 'ℹ️  INFORMATIONAL: Pages with Noindex (Intentionally Not Indexed)'));
        console.log('='.repeat(80));
        console.log(`${results.noindexPages.length} pages have noindex directive (this is OK if intentional)\n`);

        results.noindexPages.slice(0, 5).forEach((page, i) => {
            console.log(`${i + 1}. ${page.path} (${page.directive})`);
        });

        if (results.noindexPages.length > 5) {
            console.log(`   ... and ${results.noindexPages.length - 5} more pages`);
        }
    }

    // Final Recommendation
    console.log('\n' + '='.repeat(80));
    console.log(c('cyan', '🎯 GOOGLE INDEXING READINESS'));
    console.log('='.repeat(80));

    if (results.schemaErrors.length > 0) {
        console.log(c('yellow', '⚠️  CURRENT STATUS: NOT READY'));
        console.log(c('yellow', `   Reason: ${results.schemaErrors.length} pages have invalid schemas in current public/ build`));
        console.log(c('yellow', '   Fix schema output (or remove invalid schema), rebuild, then re-check.'));
    } else if (results.canonicalConflicts.length > 0) {
        console.log(c('yellow', '⚠️  STATUS: MOSTLY READY'));
        console.log(c('yellow', `   ${results.canonicalConflicts.length} pages have canonical+noindex conflicts`));
        console.log('   This is a warning, not a blocker');
    } else {
        console.log(c('green', '✅ STATUS: FULLY READY FOR GOOGLE INDEXING'));
        console.log(c('green', '   No critical issues found'));
        console.log(c('green', `   ${results.validPages} pages will index correctly`));
    }

    console.log('\n' + '='.repeat(80));
    console.log(c('cyan', '📋 RECOMMENDED NEXT STEPS'));
    console.log('='.repeat(80));

    if (results.schemaErrors.length > 0) {
        console.log('1. Fix templates/content to remove invalid schema output');
        console.log('2. Rebuild: hugo --minify --gc');
        console.log('3. Run: node validate-schema.js');
        console.log('4. Re-run: node google-indexability-check.js');
    } else {
        console.log('1. ✅ Site is ready for Google indexing');
        console.log('2. Submit sitemap.xml to Google Search Console');
        console.log('3. Request indexing for important pages');
        console.log('4. Monitor GSC reports regularly');
    }

    console.log('\n' + '='.repeat(80) + '\n');

    // Exit code
    if (results.schemaErrors.length > 0) {
        console.log(c('yellow', '⚠️  Exit code 1 because critical issues were found'));
        process.exit(1);
    }
}

checkGoogleIndexability().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
});
