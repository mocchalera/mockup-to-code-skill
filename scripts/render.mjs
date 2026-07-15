#!/usr/bin/env node
/**
 * render: render an HTML page at a FIXED viewport (DPR=1) and collect both
 * a full-page screenshot and the DOMRect of every [data-el] element.
 *
 * This is the "answer side" of the box-diff loop: the mockup gives expected
 * boxes (element manifest), the DOM gives actual boxes. One launch, one pass.
 *
 * Usage:
 *   node render.mjs --html site/index.html \
 *     [--viewport 1440x900] [--out-png work/rendered.png] \
 *     [--out-rects work/rects.json] [--wait 200]
 *
 * rects.json:
 *   { "docHeight": 3120, "rects": [ { "el": "hero-title", "x":120, "y":180,
 *     "w":680, "h":160, "fontSize": "88px", "lineHeight": "84px",
 *     "fontFamily": "Noto Sans JP" } ] }
 *
 * Browser discovery: CHROME_PATH > playwright-managed Chromium > system
 * Chrome/Chromium/Edge (macOS + Linux) — see _browser.mjs. If none exists,
 * use MCP Playwright or the in-app browser instead (SKILL.md).
 */
import { writeFile, mkdir } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { launchBrowser, settleLazyImages } from './_browser.mjs';

const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
  args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
}
if (!args.html && !args.url) {
  console.error('usage: node render.mjs --html <file> [--viewport WxH] [--out-png f] [--out-rects f] [--wait ms]');
  process.exit(1);
}

const [vw, vh] = (args.viewport || '1440x900').split('x').map(Number);
const { browser, executable } = await launchBrowser();
try {
  const page = await browser.newPage({
    viewport: { width: vw, height: vh },
    deviceScaleFactor: 1,
  });
  const target = args.url || pathToFileURL(resolve(args.html)).href;
  await page.goto(target, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await settleLazyImages(page);
  await page.waitForTimeout(Number(args.wait || 150));

  const data = await page.evaluate(() => {
    const rects = [...document.querySelectorAll('[data-el]')].map((e) => {
      const r = e.getBoundingClientRect();
      const cs = getComputedStyle(e);
      return {
        el: e.dataset.el,
        x: Math.round(r.x * 10) / 10,
        y: Math.round((r.y + window.scrollY) * 10) / 10,
        w: Math.round(r.width * 10) / 10,
        h: Math.round(r.height * 10) / 10,
        fontSize: cs.fontSize,
        lineHeight: cs.lineHeight,
        fontFamily: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
      };
    });
    return { docHeight: document.documentElement.scrollHeight, rects };
  });

  if (args['out-rects']) {
    await mkdir(dirname(resolve(args['out-rects'])), { recursive: true });
    await writeFile(args['out-rects'], JSON.stringify(data, null, 2));
  }
  if (args['out-png']) {
    await mkdir(dirname(resolve(args['out-png'])), { recursive: true });
    await page.screenshot({ path: args['out-png'], fullPage: true });
  }
  console.log(JSON.stringify({
    ok: true,
    browser: executable,
    viewport: `${vw}x${vh}@1`,
    docHeight: data.docHeight,
    elements: data.rects.length,
    png: args['out-png'] || null,
    rects: args['out-rects'] || null,
  }, null, 2));
} finally {
  await browser.close();
}
