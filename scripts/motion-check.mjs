#!/usr/bin/env node
/** Runtime QA for an explicitly required motion plan. */
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { launchBrowser, settleLazyImages } from './_browser.mjs';

function argsOf(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) continue;
    const key = argv[i].slice(2);
    out[key] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
  }
  return out;
}

const args = argsOf(process.argv.slice(2));
if ((!args.html && !args.url) || !args.manifest) {
  console.error('usage: node motion-check.mjs --html page.html --manifest manifest.json [--viewports 1440x900,390x844] --out report.json');
  process.exit(2);
}
const manifestBytes = await readFile(args.manifest);
const manifest = JSON.parse(manifestBytes.toString('utf8'));
const motion = manifest.motion || { required: false };
const manifestReceipt = {
  path: args.manifest,
  sha256: createHash('sha256').update(manifestBytes).digest('hex'),
  size: manifestBytes.length,
};
const baseReport = {
  schemaVersion: 'motion-report/v1',
  manifest: manifestReceipt,
  required: motion.required === true,
  visualQaState: motion.visualQaState || null,
};
if (motion.required !== true) {
  const report = { ...baseReport, status: 'not_required', checks: [] };
  if (args.out) {
    await mkdir(dirname(resolve(args.out)), { recursive: true });
    await writeFile(args.out, JSON.stringify(report, null, 2) + '\n');
  }
  console.log(JSON.stringify(report, null, 2));
  process.exit(0);
}

const targetUrl = args.url || pathToFileURL(resolve(args.html)).href;
const viewports = String(args.viewports || '1440x900,390x844')
  .split(',').map((value) => value.split('x').map(Number));
const byId = Object.fromEntries((manifest.elements || []).map((row) => [row.id, row]));
const targetIds = [...new Set((motion.motifs || []).flatMap((row) => row.targets || []))];
const targetEls = targetIds.map((id) => byId[id]?.el).filter(Boolean);
const criticalEls = (manifest.elements || [])
  .filter((row) => ['fv-critical', 'section-critical'].includes(row.qaPriority) && row.el)
  .map((row) => row.el);
const maxWait = Math.min(1500, Math.max(250, ...(motion.motifs || []).map((row) =>
  Number(row.durationMs || 0) + Number(row.delayMs || 0) + Number(row.staggerMs || 0) * Math.max(0, (row.targets || []).length - 1)
)));
const checks = [];
const { browser, executable } = await launchBrowser();
try {
  for (const [width, height] of viewports) {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    await page.addInitScript(() => {
      window.__motionEvents = [];
      const capture = (event) => window.__motionEvents.push({
        type: event.type,
        el: event.target?.getAttribute?.('data-el') || null,
        name: event.animationName || event.propertyName || null,
        at: performance.now(),
      });
      document.addEventListener('animationstart', capture, true);
      document.addEventListener('transitionrun', capture, true);
      const original = Element.prototype.animate;
      Element.prototype.animate = function (...args) {
        window.__motionEvents.push({ type: 'web-animation', el: this.getAttribute?.('data-el') || null, at: performance.now() });
        return original.apply(this, args);
      };
    });
    await page.goto(targetUrl, { waitUntil: 'networkidle' });
    await settleLazyImages(page);
    for (const el of targetEls) {
      const locator = page.locator(`[data-el="${el}"]`).first();
      if (await locator.count()) await locator.scrollIntoViewIfNeeded();
      await page.waitForTimeout(80);
    }
    await page.waitForTimeout(maxWait);
    const normal = await page.evaluate(({ targetEls, criticalEls }) => {
      const missing = targetEls.filter((el) => !document.querySelector(`[data-el="${el}"]`));
      const visible = (el) => {
        const node = document.querySelector(`[data-el="${el}"]`);
        if (!node) return false;
        const cs = getComputedStyle(node); const rect = node.getBoundingClientRect();
        return cs.display !== 'none' && cs.visibility !== 'hidden' && Number(cs.opacity) > 0 && rect.width > 0 && rect.height > 0;
      };
      const badLinks = [...document.querySelectorAll('a[data-el], a[href]')]
        .filter((node) => {
          const href = node.getAttribute('href');
          if (!href || href === '#' || href.toLowerCase().startsWith('javascript:')) return true;
          return href.startsWith('#') && !document.getElementById(href.slice(1));
        }).map((node) => ({ el: node.getAttribute('data-el'), href: node.getAttribute('href') }));
      return {
        missing,
        hiddenCritical: criticalEls.filter((el) => !visible(el)),
        badLinks,
        events: window.__motionEvents || [],
      };
    }, { targetEls, criticalEls });
    checks.push({ id: `normal-${width}`, status: normal.missing.length || normal.hiddenCritical.length || normal.badLinks.length || !normal.events.some((event) => targetEls.includes(event.el)) ? 'needs_work' : 'pass', ...normal });
    await page.close();

    const reduced = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    await reduced.emulateMedia({ reducedMotion: 'reduce' });
    await reduced.goto(targetUrl, { waitUntil: 'networkidle' });
    await settleLazyImages(reduced);
    const reducedResult = await reduced.evaluate((criticalEls) => {
      const hidden = criticalEls.filter((el) => {
        const node = document.querySelector(`[data-el="${el}"]`);
        if (!node) return true;
        const cs = getComputedStyle(node); const rect = node.getBoundingClientRect();
        return cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0 || rect.width === 0 || rect.height === 0;
      });
      const activeMeaningful = document.getAnimations({ subtree: true }).filter((animation) => {
        const el = animation.effect?.target?.getAttribute?.('data-el');
        const duration = Number(animation.effect?.getTiming?.().duration || 0);
        return el && criticalEls.includes(el) && duration > 10;
      }).map((animation) => animation.effect?.target?.getAttribute?.('data-el'));
      return { hiddenCritical: hidden, activeMeaningful };
    }, criticalEls);
    checks.push({ id: `reduced-${width}`, status: reducedResult.hiddenCritical.length || reducedResult.activeMeaningful.length ? 'needs_work' : 'pass', ...reducedResult });
    await reduced.close();
  }

  const noJs = await browser.newPage({ viewport: { width: 390, height: 844 }, javaScriptEnabled: false });
  await noJs.goto(targetUrl, { waitUntil: 'domcontentloaded' });
  const noJsResult = await noJs.evaluate((criticalEls) => ({
    hiddenCritical: criticalEls.filter((el) => {
      const node = document.querySelector(`[data-el="${el}"]`);
      if (!node) return true;
      const cs = getComputedStyle(node); const rect = node.getBoundingClientRect();
      return cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0 || rect.width === 0 || rect.height === 0;
    }),
  }), criticalEls);
  checks.push({ id: 'javascript-disabled', status: noJsResult.hiddenCritical.length ? 'needs_work' : 'pass', ...noJsResult });
  await noJs.close();
} finally {
  await browser.close();
}

const status = checks.every((row) => row.status === 'pass') ? 'pass' : 'needs_work';
const report = { ...baseReport, status, browser: executable, checks };
if (args.out) {
  await mkdir(dirname(resolve(args.out)), { recursive: true });
  await writeFile(args.out, JSON.stringify(report, null, 2) + '\n');
}
console.log(JSON.stringify(report, null, 2));
process.exit(status === 'pass' ? 0 : 1);
