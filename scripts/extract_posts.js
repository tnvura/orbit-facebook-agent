#!/usr/bin/env node
/**
 * extract_posts.js — Facebook Group Post Extractor with JS Pre-filter
 *
 * Uses Playwright Node.js API to extract posts from a Facebook group feed,
 * applies Thai keyword filter in-browser (zero LLM tokens), deduplicates.
 *
 * Usage:
 *   node scripts/extract_posts.js <group_url> <profile_path> <keywords_path> <processed_ids_path>
 *
 * Output: JSON array to stdout — [{id, author, text, url, timestamp}, ...]
 */

const { chromium } = require('/opt/homebrew/lib/node_modules/@playwright/cli/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const [, , groupUrl, profilePath, keywordsPath, processedIdsPath] = process.argv;

if (!groupUrl || !profilePath || !keywordsPath || !processedIdsPath) {
  process.stderr.write('Usage: node extract_posts.js <group_url> <profile_path> <keywords_path> <processed_ids_path>\n');
  process.exit(1);
}

function loadProcessedIds(filePath) {
  const abs = path.resolve(filePath);
  if (!fs.existsSync(abs)) return new Set();
  return new Set(
    fs.readFileSync(abs, 'utf8').split('\n').map(l => l.trim()).filter(Boolean)
  );
}

async function main() {
  const keywords = JSON.parse(fs.readFileSync(path.resolve(keywordsPath), 'utf8'));
  const processedIds = loadProcessedIds(processedIdsPath);
  const absProfile = path.resolve(profilePath);

  process.stderr.write('Opening browser...\n');
  const context = await chromium.launchPersistentContext(absProfile, {
    headless: false,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });

  const page = context.pages()[0] || (await context.newPage());

  process.stderr.write(`Navigating to ${groupUrl}...\n`);
  await page.goto(groupUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

  process.stderr.write('Waiting for feed to load...\n');
  await page.waitForTimeout(5000);

  process.stderr.write('Scrolling feed...\n');
  for (let i = 0; i < 5; i++) {
    await page.evaluate(() => window.scrollBy(0, 1500));
    await page.waitForTimeout(2500);
  }

  process.stderr.write('Applying JS filter...\n');

  const candidates = await page.evaluate(({ questionMarkers, accountingTerms, excludeTerms }) => {
    function containsAny(text, terms) {
      const lower = text.toLowerCase();
      return terms.some(t => lower.includes(t.toLowerCase()));
    }

    const results = [];
    const postLinks = document.querySelectorAll('a[href*="/posts/"]');
    const seen = new Set();

    for (const link of postLinks) {
      const href = link.href || '';
      const match = href.match(/\/posts\/(\d+)/);
      if (!match) continue;
      const postId = match[1];
      if (seen.has(postId)) continue;
      seen.add(postId);

      let article = link.closest('div[role="article"]') || link.closest('div[data-pagelet]');
      if (!article) continue;

      const msgEl = article.querySelector('div[data-ad-comet-preview="message"]');
      const text = msgEl ? msgEl.innerText.trim() : '';
      if (text.length < 20) continue;

      const headings = article.querySelectorAll('h3, h2');
      const author = headings.length > 0 ? headings[0].innerText.trim() : 'Unknown';

      const timeLinks = article.querySelectorAll('a[href*="?__cft__"]');
      let timestamp = '';
      for (const tl of timeLinks) {
        const t = tl.innerText.trim();
        if (t && (t.includes('m') || t.includes('h') || t.includes('d') || t.includes('w'))) {
          timestamp = t;
          break;
        }
      }

      const cleanUrl = href.split('?')[0];

      if (containsAny(text, excludeTerms)) continue;

      const hasQuestion = containsAny(text, questionMarkers);
      const hasAccounting = containsAny(text, accountingTerms);

      if (hasQuestion && hasAccounting) {
        results.push({ id: postId, author, text: text.substring(0, 500), url: cleanUrl, timestamp });
      }
    }

    return results;
  }, {
    questionMarkers: keywords.question_markers,
    accountingTerms: keywords.accounting_tax_terms,
    excludeTerms: keywords.exclude_terms,
  });

  await context.close();

  const newCandidates = candidates.filter(c => !processedIds.has(c.id));
  process.stderr.write(`Found ${candidates.length} raw matches, ${newCandidates.length} new after dedup\n`);
  process.stdout.write(JSON.stringify(newCandidates, null, 2) + '\n');
}

main().catch(err => {
  process.stderr.write(`Error: ${err.message}\n`);
  process.exit(1);
});
