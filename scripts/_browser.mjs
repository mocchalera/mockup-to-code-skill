/**
 * _browser.mjs — shared Chromium discovery + launch for render.mjs and
 * visual-check.mjs.
 *
 * Discovery order:
 *   1. CHROME_PATH env var
 *   2. playwright-managed Chromium (if installed via setup_env.sh)
 *   3. system browsers: macOS Google Chrome / Chromium / Edge,
 *      Linux google-chrome / chromium
 *
 * If none is found, throws with actionable alternatives (system Chrome,
 * MCP Playwright / in-app browser) instead of a bare launch error.
 */
import { chromium } from 'playwright-core';
import { existsSync } from 'node:fs';
import { open, stat, unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SYSTEM_CANDIDATES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium-browser',
  '/usr/bin/chromium',
];
const LOCK_PATH = join(tmpdir(), 'mockup-to-code-browser.lock');
const LOCK_STALE_MS = 120_000;
const LAUNCH_BACKOFF_MS = [5_000, 15_000, 30_000];

const sleep = (ms) => new Promise((resolveSleep) => setTimeout(resolveSleep, ms));

async function acquireLaunchLock() {
  while (true) {
    try {
      const handle = await open(LOCK_PATH, 'wx');
      await handle.writeFile(JSON.stringify({
        pid: process.pid,
        startedAt: new Date().toISOString(),
      }));
      return async () => {
        await handle.close().catch(() => {});
        await unlink(LOCK_PATH).catch((err) => {
          if (err?.code !== 'ENOENT') throw err;
        });
      };
    } catch (err) {
      if (err?.code !== 'EEXIST') throw err;
      try {
        const info = await stat(LOCK_PATH);
        if (Date.now() - info.mtimeMs > LOCK_STALE_MS) {
          console.error(`[mockup-to-code] taking over stale browser launch lock: ${LOCK_PATH}`);
          await unlink(LOCK_PATH).catch((unlinkErr) => {
            if (unlinkErr?.code !== 'ENOENT') throw unlinkErr;
          });
          continue;
        }
      } catch (statErr) {
        if (statErr?.code === 'ENOENT') continue;
        throw statErr;
      }
      await sleep(250);
    }
  }
}

async function launchWithLock(options) {
  const release = await acquireLaunchLock();
  try {
    return await chromium.launch(options);
  } finally {
    await release();
  }
}

export function findChromium() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) {
    return { path: process.env.CHROME_PATH, source: 'CHROME_PATH' };
  }
  try {
    const p = chromium.executablePath();
    if (p && existsSync(p)) return { path: p, source: 'playwright' };
  } catch { /* registry empty — fall through */ }
  for (const p of SYSTEM_CANDIDATES) {
    if (existsSync(p)) return { path: p, source: 'system' };
  }
  return null;
}

export async function launchBrowser() {
  const skillRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const libsDir = join(skillRoot, '.libs');
  const env = { ...process.env };
  if (existsSync(libsDir)) {
    env.LD_LIBRARY_PATH = libsDir + (env.LD_LIBRARY_PATH ? ':' + env.LD_LIBRARY_PATH : '');
  }

  const found = findChromium();
  if (!found) {
    throw new Error(
      'No Chromium found. Options:\n' +
      '  1. point CHROME_PATH at an installed Chrome, e.g.\n' +
      '     CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"\n' +
      '  2. bash scripts/setup_env.sh  (installs playwright-managed Chromium)\n' +
      '  3. no local browser at all: verify via MCP Playwright / the in-app\n' +
      '     browser instead of render.mjs (see SKILL.md "Rendering environments")'
    );
  }
  const launchOptions = {
    executablePath: found.path,
    env,
    args: ['--no-sandbox', '--force-color-profile=srgb', '--font-render-hinting=none', '--hide-scrollbars'],
  };
  let lastError = null;
  for (let attempt = 1; attempt <= LAUNCH_BACKOFF_MS.length + 1; attempt++) {
    console.error(`[mockup-to-code] browser launch attempt ${attempt}/${LAUNCH_BACKOFF_MS.length + 1} (${found.source}: ${found.path})`);
    try {
      const browser = await launchWithLock(launchOptions);
      return { browser, executable: found };
    } catch (err) {
      lastError = err;
      const backoff = LAUNCH_BACKOFF_MS[attempt - 1];
      if (!backoff) break;
      console.error(`[mockup-to-code] browser launch attempt ${attempt} failed: ${err.message}`);
      console.error(`[mockup-to-code] retrying browser launch in ${Math.round(backoff / 1000)}s`);
      await sleep(backoff);
    }
  }
  throw new Error(
    'BROWSER_LAUNCH_FAILED_TRANSPORT_FALLBACK: Chromium launch failed after ' +
    `${LAUNCH_BACKOFF_MS.length + 1} attempts. Do not retry render.mjs or ` +
    'visual-check.mjs in a loop; fall back to the transport ladder: MCP ' +
    'Playwright / CLI screenshot / static checks. Last error: ' +
    (lastError?.message || lastError)
  );
}

/**
 * Force-load lazy images so file-based renders/checks don't report
 * below-the-fold `loading="lazy"` images as unloaded (false failures).
 * Sets loading=eager, scrolls through the document (triggers
 * IntersectionObserver-based loaders too), returns to top, then waits for
 * every image to settle (capped at `timeout` ms). Genuinely broken images
 * stay incomplete/naturalWidth=0 and are still caught by the images check.
 */
export async function settleLazyImages(page, timeout = 8000) {
  await page.evaluate(async () => {
    for (const img of document.images) img.loading = 'eager';
    const step = Math.max(200, window.innerHeight);
    for (let y = 0; y <= document.documentElement.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 40));
    }
    window.scrollTo(0, 0);
  });
  await page
    .waitForFunction(() => [...document.images].every((i) => i.complete), undefined, { timeout })
    .catch(() => { /* broken images are the images check's job, not ours */ });
}
