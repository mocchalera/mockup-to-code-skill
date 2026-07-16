#!/usr/bin/env node
/**
 * visual-check: INTENT verification for hybrid mode (box diff is geometry;
 * this checks that the design's intent survives in the real DOM).
 *
 * Checks per viewport:
 *   - images:      every <img> loaded (complete + naturalWidth>0), no failed
 *                  requests. Lazy images are force-loaded (eager + full-page
 *                  scroll) first, so a failure here is a genuinely broken image.
 *   - no-h-scroll: document/body do not scroll horizontally; root overflow
 *                  suppression cannot hide clipped meaningful content
 *   - responsive-visible-ratio: non-decorative manifest/semantic content keeps
 *                  at least 98% of its horizontal DOMRect inside the viewport
 *   - same-document-fragment: local #fragment links resolve to an id/name
 *   - copy:        every structural manifest text.content string exists in
 *                  page text (lettering-decal text is judged by crop pairs)
 *   - elements:    every manifest data-el exists in the DOM
 *   - surface-visible-owner: a manifested raster surface must be the visible
 *                  painting owner, never an opacity:0 measurement proxy
 *   - generic-symbol-standin: source-specific line art/UI/card craft may not
 *                  collapse into emoji or Unicode-symbol-only leaf nodes
 *   - fv-layer:    elements with backgroundBehavior full-bleed/generated are
 *                  position:absolute|fixed and span >=98% of the viewport width
 *                  (a full-bleed hero photo must be a background LAYER, not a card)
 *   - must-not-cover: declared mustNotCover pairs do not intersect
 *   - micro-geometry: declared circles stay round, triangles keep exactly
 *                  three vertices, and attention rays sit outside their
 *                  target on the declared side while aligning radially
 *   - surface-edge-contact: source-evidenced full-bleed card artwork actually
 *                  reaches the declared consumer edges instead of inheriting
 *                  generic card padding
 *   - layout-law: absolute/fixed/sticky [data-el] elements must be declared
 *                  with matching positioning or use an allowed decorative/layer role
 *   - typography-transform: structural manifest text may not use CSS
 *                  transform to scale/skew/translate into its measured box;
 *                  a documented source-intent/decorative exception is required
 *   - font-family: the rendered family must contain the frozen manifest family
 *   - font-face-load: non-system critical type must resolve to a loaded face;
 *                  a fallback rendered under the requested family string fails
 *   - font-weight-face: computed/requested weight must be a delivered static
 *                  face or fall inside the declared variable-weight range
 *   - typography-hierarchy: source-measured size and weight contrast between
 *                  display/lead/label roles must survive in the browser
 *   - typography-whitespace: source-measured negative space between text
 *                  blocks may not collapse into generic section spacing
 *   - typography-extreme-scale: deliberately oversized dominant type may not
 *                  be timidly capped below its source viewport ratio
 *   - typography-line-count: fv-critical structural text keeps the comp's
 *                  expectedVisualLineCount at the canonical manifest viewport
 *   - text-overlap: substantial structural-text intersections are hard failures
 *                  unless the manifest explicitly declares the overlap intent
 *   - clip-owner: a declared frame-local layer must be clipped by its owner
 *   - widths mode: --widths audits responsive widths for no horizontal scroll
 *                  and dead right gutters from left-pinned fixed canvases
 *   - section-overflow-policy: multi-frame section clipping must match the
 *                  pageComposition owner contract; global overflow:hidden is
 *                  not a substitute for designing cross-section handoffs
 *   - overlap-warnings: text elements that intersect WITHOUT a declared
 *                  overlaps/overlapIntent (defect candidates, not hard fails)
 *   - mobile (viewport width < 768):
 *       fv-critical headings keep font-size >= --min-heading-px (default 28)
 *       cta / fv-critical buttons are rendered and visible
 *
 * Usage:
 *   node visual-check.mjs --html work/site/index.html \
 *     [--manifest work/manifest.json] [--viewports 1440x900,390x844] \
 *     [--widths [320,390,768,1024,1440,1728]] \
 *     [--min-heading-px 28] [--out work/reports/visual-check.json]
 *
 * Exit code 0 = all hard checks pass (warnings allowed), 1 = violations.
 * Keep visual-check.json in work/reports/ as completion evidence.
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { launchBrowser, settleLazyImages } from './_browser.mjs';

function parseArgs(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const eq = token.indexOf('=');
    if (eq !== -1) {
      parsed[token.slice(2, eq)] = token.slice(eq + 1);
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (next && !next.startsWith('--')) {
      parsed[key] = next;
      i++;
    } else {
      parsed[key] = true;
    }
  }
  return parsed;
}

const args = parseArgs(process.argv.slice(2));
if (!args.html && !args.url) {
  console.error('usage: node visual-check.mjs --html <file> [--manifest m.json] [--viewports 1440x900,390x844] [--widths [320,390,768,1024,1440,1728]] [--out f.json]');
  process.exit(1);
}

const manifest = args.manifest
  ? JSON.parse(await readFile(args.manifest, 'utf8'))
  : { elements: [] };
const strictHybrid = manifest.mode === 'hybrid' &&
  (manifest.referenceImages || []).filter((row) => row?.use === 'section-comp').length >= 2;
const manifestBytes = args.manifest ? await readFile(args.manifest) : null;
const manifestSha256 = manifestBytes ? createHash('sha256').update(manifestBytes).digest('hex') : null;
const workRoot = args.manifest ? resolve(dirname(args.manifest)) : null;
const readJsonIfPresent = async (path) => {
  try { return JSON.parse(await readFile(path, 'utf8')); } catch { return null; }
};
const contractDoctor = workRoot ? await readJsonIfPresent(resolve(workRoot, 'reports/contract-doctor.json')) : null;
const assetPreflight = workRoot ? await readJsonIfPresent(resolve(workRoot, 'reports/asset-preflight.json')) : null;
const receiptMatches = (report) => report?.inputs?.manifest?.sha256 === manifestSha256;
const adoptedAssetEntries = (manifest.elements || []).flatMap((element) => {
  const payloadName = ({ generated: 'generatedAsset', replace: 'replacedAsset', 'crop-asset': 'croppedAsset' })[element?.assetStrategy];
  const path = payloadName ? element?.[payloadName]?.workspacePath : null;
  return typeof path === 'string' && path ? [{ elementId: String(element?.id || '<missing-id>'), path }] : [];
});
const assetReceiptsMatch = async (report) => {
  const receipts = report?.inputs?.assets;
  if (!Array.isArray(receipts) || receipts.length !== adoptedAssetEntries.length || !workRoot) return false;
  for (let index = 0; index < receipts.length; index++) {
    const receipt = receipts[index];
    const expected = adoptedAssetEntries[index];
    if (receipt?.elementId !== expected.elementId || receipt?.path !== expected.path) return false;
    try {
      const bytes = await readFile(resolve(workRoot, expected.path));
      if (receipt.size !== bytes.length || receipt.sha256 !== createHash('sha256').update(bytes).digest('hex')) return false;
    } catch {
      return false;
    }
  }
  return true;
};
const assetPreflightAssetReceiptsMatch = strictHybrid ? await assetReceiptsMatch(assetPreflight) : true;
const pipelineContract = strictHybrid ? {
  pass: contractDoctor?.status === 'pass' && contractDoctor?.implementationAllowed === true &&
    assetPreflight?.implementationAllowed === true && receiptMatches(contractDoctor) &&
    receiptMatches(assetPreflight) && assetPreflightAssetReceiptsMatch,
  contractDoctor: contractDoctor?.status || 'missing',
  assetPreflight: assetPreflight?.status || 'missing',
  contractDoctorReceiptMatches: receiptMatches(contractDoctor),
  assetPreflightReceiptMatches: receiptMatches(assetPreflight),
  assetPreflightAssetReceiptsMatch,
} : { pass: true, notRequired: true };
const defaultWidths = [320, 390, 768, 1024, 1440, 1728];
const widthMode = Object.prototype.hasOwnProperty.call(args, 'widths');
const viewports = widthMode
  ? (args.widths === true || args.widths === '' ? defaultWidths : String(args.widths).split(',').map(Number))
      .map((w) => [w, w <= 430 ? 844 : 900])
  : (args.viewports || '1440x900,390x844')
      .split(',').map((v) => v.split('x').map(Number));
const minHeadingPx = Number(args['min-heading-px'] || 28);
const sectionEls = (manifest.referenceImages || [])
  .filter((ri) => ri.use === 'section-comp' && ri.section)
  .map((ri) => ri.section);
const pageSectionContracts = Object.fromEntries(
  (manifest.pageComposition?.sections || [])
    .filter((section) => section?.section)
    .map((section) => [section.section, section])
);

const { browser, executable } = await launchBrowser();
const results = [];
try {
  for (const [vw, vh] of viewports) {
    const page = await browser.newPage({ viewport: { width: vw, height: vh }, deviceScaleFactor: 1 });
    const failedRequests = [];
    page.on('requestfailed', (r) => failedRequests.push({ url: r.url(), error: r.failure()?.errorText }));
    const target = args.url || pathToFileURL(resolve(args.html)).href;
    await page.goto(target, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    await settleLazyImages(page);
    await page.waitForTimeout(150);

    const r = await page.evaluate(({ elements, detailInventory, typographyComposition, sectionEls, pageSectionContracts, minHeadingPx, isMobile, runDeadGutter, canonicalWidth, strictHybrid }) => {
      const norm = (s) => (s || '').replace(/\s+/g, '');
      const rectOf = (el) => {
        const e = document.querySelector(`[data-el="${el}"]`);
        if (!e) return null;
        const b = e.getBoundingClientRect();
        return { e, x: b.x, y: b.y + window.scrollY, w: b.width, h: b.height };
      };
      const visible = (el) => {
        const cs = getComputedStyle(el);
        const b = el.getBoundingClientRect();
        return cs.display !== 'none' && cs.visibility !== 'hidden' &&
          Number(cs.opacity) !== 0 && b.width > 0 && b.height > 0;
      };
      const rectBox = (el) => {
        const b = el.getBoundingClientRect();
        return {
          left: b.left,
          top: b.top + window.scrollY,
          right: b.right,
          bottom: b.bottom + window.scrollY,
          width: b.width,
          height: b.height,
        };
      };
      const roundedBox = (box) => Object.fromEntries(
        Object.entries(box).map(([k, v]) => [k, Math.round(v * 10) / 10])
      );
      const contentBoxOf = (section) => {
        let nodes = [...section.querySelectorAll('*')].filter(visible);
        if (!nodes.length && visible(section)) nodes = [section];
        if (!nodes.length) return null;
        const boxes = nodes.map(rectBox);
        const left = Math.min(...boxes.map((b) => b.left));
        const top = Math.min(...boxes.map((b) => b.top));
        const right = Math.max(...boxes.map((b) => b.right));
        const bottom = Math.max(...boxes.map((b) => b.bottom));
        return { left, top, right, bottom, width: right - left, height: bottom - top };
      };
      const intersect = (a, b) => {
        const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
        const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
        return w > 0 && h > 0 ? w * h : 0;
      };
      const violations = [];
      const warnings = [];
      const byEl = Object.fromEntries(elements.filter((el) => el.el).map((el) => [el.el, el]));
      const byId = Object.fromEntries(elements.filter((el) => el.id).map((el) => [el.id, el]));
      const decorativeLayerRoles = new Set([
        'background-photo',
        'photo-overlay-gradient',
        'decorative-outline-type',
        'accent-band',
        'decorative',
      ]);
      const structuralText = (entry) => Boolean(
        entry?.text?.content &&
        entry.mediaClass !== 'lettering-decal' &&
        entry.textRecreation !== 'lettering-decal'
      );
      const fontWeightNumber = (value) => {
        if (String(value).toLowerCase() === 'normal') return 400;
        if (String(value).toLowerCase() === 'bold') return 700;
        const parsed = Number.parseFloat(value);
        return Number.isFinite(parsed) ? parsed : null;
      };
      const normalizedFontFamily = (value) => String(value || '')
        .replace(/["']/g, '').trim().toLowerCase();
      const deliveredFontFaces = [...document.fonts].map((face) => {
        const weights = String(face.weight || '400').match(/\d+(?:\.\d+)?/g)?.map(Number) || [400];
        return {
          family: normalizedFontFamily(face.family),
          minWeight: Math.min(...weights),
          maxWeight: Math.max(...weights),
          status: face.status,
        };
      });
      const transformExceptionValid = (entry) => {
        const ex = entry?.typeSpec?.transformException;
        return Boolean(
          ex?.allowed === true &&
          ['decorative-lettering', 'source-intent-display'].includes(ex.scope) &&
          String(ex.reason || '').trim() &&
          String(ex.evidencePath || '').trim()
        );
      };
      const renderedLineCount = (node) => {
        const range = document.createRange();
        range.selectNodeContents(node);
        const rects = [...range.getClientRects()]
          .filter((rect) => rect.width > 0.5 && rect.height > 0.5)
          .sort((a, b) => a.top - b.top || a.left - b.left);
        const clusters = [];
        for (const rect of rects) {
          const rectCenter = (rect.top + rect.bottom) / 2;
          const match = clusters.find((cluster) => {
            const overlap = Math.max(
              0,
              Math.min(cluster.bottom, rect.bottom) - Math.max(cluster.top, rect.top),
            );
            const minHeight = Math.max(1, Math.min(cluster.bottom - cluster.top, rect.height));
            const clusterCenter = (cluster.top + cluster.bottom) / 2;
            const maxHeight = Math.max(cluster.bottom - cluster.top, rect.height);
            return overlap / minHeight >= 0.5 || Math.abs(clusterCenter - rectCenter) <= maxHeight * 0.4;
          });
          if (match) {
            match.top = Math.min(match.top, rect.top);
            match.bottom = Math.max(match.bottom, rect.bottom);
          } else {
            clusters.push({ top: rect.top, bottom: rect.bottom });
          }
        }
        return clusters.length || (visible(node) ? 1 : 0);
      };
      const renderedLineStrings = (node) => {
        const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, {
          acceptNode(textNode) {
            if (!textNode.nodeValue?.trim()) return NodeFilter.FILTER_REJECT;
            if (['SCRIPT', 'STYLE'].includes(textNode.parentElement?.tagName)) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
          },
        });
        const glyphs = [];
        let textNode;
        while ((textNode = walker.nextNode())) {
          for (let index = 0; index < textNode.nodeValue.length; index++) {
            const char = textNode.nodeValue[index];
            if (/\s/.test(char)) continue;
            const range = document.createRange();
            range.setStart(textNode, index);
            range.setEnd(textNode, index + 1);
            const rect = range.getBoundingClientRect();
            if (rect.width > 0.2 && rect.height > 0.2) glyphs.push({ char, rect });
          }
        }
        glyphs.sort((a, b) => a.rect.top - b.rect.top || a.rect.left - b.rect.left);
        const lines = [];
        for (const glyph of glyphs) {
          const center = (glyph.rect.top + glyph.rect.bottom) / 2;
          let line = lines.find((candidate) => Math.abs(candidate.center - center) <= Math.max(candidate.height, glyph.rect.height) * 0.45);
          if (!line) {
            line = { center, height: glyph.rect.height, glyphs: [] };
            lines.push(line);
          }
          line.glyphs.push(glyph);
          line.center = (line.center * (line.glyphs.length - 1) + center) / line.glyphs.length;
          line.height = Math.max(line.height, glyph.rect.height);
        }
        return lines
          .sort((a, b) => a.center - b.center)
          .map((line) => line.glyphs.sort((a, b) => a.rect.left - b.rect.left).map((glyph) => glyph.char).join(''));
      };

      // images
      const badImgs = [...document.images]
        .filter((i) => !i.complete || i.naturalWidth === 0)
        .map((i) => i.currentSrc || i.src);
      if (badImgs.length) violations.push({ check: 'images', detail: badImgs });

      // Horizontal integrity must not trust documentElement.scrollWidth alone.
      // `overflow-x:hidden|clip` on html/body can reduce the reported scroll
      // width while a fixed-width content grid is still visibly amputated.
      // Inspect document/body widths, root computed overflow, and the horizontal
      // visible ratio of meaningful DOMRects. Explicit decorative/full-bleed
      // layers are excluded; reachable content inside an actual x-scroller is
      // also excluded because it is not clipped from the user.
      const de = document.documentElement;
      const body = document.body;
      const htmlOverflowX = getComputedStyle(de).overflowX;
      const bodyOverflowX = getComputedStyle(body).overflowX;
      const suppressingValues = new Set(['hidden', 'clip']);
      const rootSuppressesHorizontalOverflow =
        suppressingValues.has(htmlOverflowX) || suppressingValues.has(bodyOverflowX);
      const scrollWidths = {
        documentElement: de.scrollWidth,
        body: body.scrollWidth,
        viewport: window.innerWidth,
      };
      const insideHorizontalScroller = (node) => {
        for (let parent = node.parentElement; parent && parent !== body; parent = parent.parentElement) {
          const cs = getComputedStyle(parent);
          if (['auto', 'scroll'].includes(cs.overflowX) && parent.scrollWidth > parent.clientWidth + 1) {
            return true;
          }
        }
        return false;
      };
      const entryIsIntentionalVisualBleed = (entry, node) => Boolean(
        entry?.role === 'decoration' ||
        entry?.mediaClass === 'lettering-decal' ||
        entry?.textRecreation === 'lettering-decal' ||
        ['full-bleed', 'generated'].includes(entry?.backgroundBehavior) ||
        decorativeLayerRoles.has(entry?.layerRole) ||
        node.getAttribute('aria-hidden') === 'true' ||
        ['none', 'presentation'].includes(node.getAttribute('role'))
      );
      const meaningfulCandidates = new Map();
      for (const entry of elements) {
        if (!entry?.el) continue;
        const node = document.querySelector(`[data-el="${entry.el}"]`);
        if (node) meaningfulCandidates.set(node, entry);
      }
      const semanticSelector = [
        'a[href]', 'button', 'input', 'select', 'textarea',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li',
        'article', 'main', 'nav', 'figure', 'img', 'table', '[role]',
      ].join(',');
      for (const node of document.querySelectorAll(semanticSelector)) {
        const owner = node.closest('[data-el]');
        const ownerEntry = owner ? byEl[owner.dataset.el] : null;
        if (ownerEntry && owner === node) continue; // exact manifested node is already audited
        if (ownerEntry && entryIsIntentionalVisualBleed(ownerEntry, owner)) continue;
        if (ownerEntry && ownerEntry.role !== 'section') continue; // manifested envelope is sufficient
        meaningfulCandidates.set(node, null);
      }
      const clippedMeaningful = [];
      for (const [node, entry] of meaningfulCandidates) {
        if (!visible(node) || entryIsIntentionalVisualBleed(entry, node)) continue;
        if (entry?.role === 'section') continue; // audit the section's content, not its canvas
        if (insideHorizontalScroller(node)) continue;
        const b = node.getBoundingClientRect();
        // Ignore conventional visually-hidden accessibility text.
        if (b.width <= 2 && b.height <= 2) continue;
        const visibleWidth = Math.max(0, Math.min(b.right, window.innerWidth) - Math.max(b.left, 0));
        const visibleRatio = b.width > 0 ? visibleWidth / b.width : 1;
        const outsideLeft = Math.max(0, -b.left);
        const outsideRight = Math.max(0, b.right - window.innerWidth);
        const outsidePx = outsideLeft + outsideRight;
        if (visibleRatio >= 0.98 || outsidePx <= 8) continue;
        clippedMeaningful.push({
          id: entry?.id || null,
          el: entry?.el || node.dataset.el || null,
          node: node.tagName.toLowerCase(),
          role: entry?.role || node.getAttribute('role') || null,
          rect: roundedBox({
            left: b.left,
            right: b.right,
            width: b.width,
            outsideLeft,
            outsideRight,
          }),
          visibleRatio: Math.round(visibleRatio * 1000) / 1000,
        });
      }
      const responsiveMetrics = {
        scrollWidths,
        rootOverflowX: {
          html: htmlOverflowX,
          body: bodyOverflowX,
          suppressesHorizontalOverflow: rootSuppressesHorizontalOverflow,
        },
        clippedMeaningfulCount: clippedMeaningful.length,
      };
      const maxScrollWidth = Math.max(scrollWidths.documentElement, scrollWidths.body);
      if (maxScrollWidth > window.innerWidth + 1 &&
          (!rootSuppressesHorizontalOverflow || clippedMeaningful.length > 0)) {
        violations.push({
          check: 'no-h-scroll',
          detail: {
            ...responsiveMetrics,
            instruction: 'Repair the overflowing flow/Grid/Flex content; do not hide it with root overflow-x.',
          },
        });
      }
      if (clippedMeaningful.length) {
        violations.push({
          check: 'responsive-visible-ratio',
          detail: {
            ...responsiveMetrics,
            minimumVisibleRatio: 0.98,
            items: clippedMeaningful,
            instruction: 'Meaningful content is outside the viewport. Reflow the layout; root overflow-x:hidden/clip is not a responsive fix.',
          },
        });
      }

      // Every same-document fragment link must resolve. This catches visually
      // polished but dead navigation such as href="#journal" with no target.
      const currentUrl = new URL(window.location.href);
      const brokenFragments = [];
      for (const link of document.querySelectorAll('a[href]')) {
        const rawHref = link.getAttribute('href') || '';
        let targetUrl;
        try {
          targetUrl = new URL(rawHref, currentUrl);
        } catch {
          continue;
        }
        const sameDocument = targetUrl.origin === currentUrl.origin &&
          targetUrl.pathname === currentUrl.pathname &&
          targetUrl.search === currentUrl.search;
        if (!sameDocument || !targetUrl.hash || targetUrl.hash === '#') continue;
        let targetName = targetUrl.hash.slice(1);
        try { targetName = decodeURIComponent(targetName); } catch { /* keep raw fragment */ }
        const targetExists = targetName.toLowerCase() === 'top' || Boolean(
          document.getElementById(targetName) ||
          [...document.getElementsByName(targetName)].some((node) => ['A', 'AREA'].includes(node.tagName))
        );
        if (!targetExists) {
          brokenFragments.push({
            href: rawHref,
            fragment: targetUrl.hash,
            text: String(link.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80),
          });
        }
      }
      if (brokenFragments.length) {
        violations.push({ check: 'same-document-fragment', detail: brokenFragments });
      }

      // responsive width integrity: catch fixed left-pinned canvases that
      // leave a large dead gutter on wide screens.
      if (runDeadGutter && window.innerWidth >= 1024) {
        const sections = sectionEls.length
          ? sectionEls.map((el) => document.querySelector(`[data-el="${el}"]`)).filter(Boolean)
          : [...document.body.children].filter(visible);
        for (const section of sections) {
          const contentBox = contentBoxOf(section);
          if (!contentBox) continue;
          const leftPinned = contentBox.left <= Math.max(16, window.innerWidth * 0.015);
          const rightEmpty = window.innerWidth - contentBox.right;
          const threshold = window.innerWidth * 0.25;
          const fixedCanvasGutter = window.innerWidth >= 1440 && rightEmpty >= 240;
          if (leftPinned && (rightEmpty > threshold || fixedCanvasGutter)) {
            violations.push({
              check: 'dead-gutter',
              el: section.dataset.el || section.tagName.toLowerCase(),
              detail: {
                contentBox: roundedBox(contentBox),
                viewportWidth: window.innerWidth,
                rightEmpty: Math.round(rightEmpty * 10) / 10,
                rightEmptyRatio: Math.round((rightEmpty / window.innerWidth) * 1000) / 1000,
                threshold: Math.round(threshold * 10) / 10,
              },
            });
          }
        }
      }

      // Section-edge ownership. A repeated `overflow:hidden` on every
      // section is the mechanical signature of treating frames as slides:
      // watermarks/curves are cut at the image boundary instead of handed to
      // the adjacent section. Only an explicit `clip` contract may clip a
      // section root; bleed/bridge policies must remain visible.
      for (const sectionEl of sectionEls) {
        const contract = pageSectionContracts[sectionEl];
        if (!contract) continue; // page_flow_check owns missing-contract evidence
        const node = document.querySelector(`[data-el="${sectionEl}"]`);
        if (!node) continue;
        const cs = getComputedStyle(node);
        const clips = ['hidden', 'clip'].includes(cs.overflowX) ||
          ['hidden', 'clip'].includes(cs.overflowY);
        const policy = contract.overflowPolicy;
        if (clips && policy !== 'clip') {
          violations.push({
            check: 'section-overflow-policy',
            el: sectionEl,
            detail: `computed overflow ${cs.overflowX}/${cs.overflowY} clips a section declared '${policy || 'undeclared'}'`,
          });
        }
        if (policy === 'clip' && !String(contract.clipReason || '').trim()) {
          violations.push({
            check: 'section-overflow-policy',
            el: sectionEl,
            detail: 'overflowPolicy:clip requires clipReason naming the frame/mask owner',
          });
        }
        if (policy === 'clip' && !clips) {
          violations.push({
            check: 'section-overflow-policy',
            el: sectionEl,
            detail: `overflowPolicy:clip declared but computed overflow is ${cs.overflowX}/${cs.overflowY}`,
          });
        }
      }

      // copy presence
      const pageText = norm(document.body.innerText);
      const missingCopy = elements
        .filter((el) => el.text?.content &&
          !['masked-ignore', 'lettering-decal'].includes(el.textRecreation) &&
          el.mediaClass !== 'lettering-decal')
        .filter((el) => !pageText.includes(norm(el.text.content).slice(0, 80)))
        .map((el) => ({ id: el.id, content: el.text.content }));
      if (missingCopy.length) violations.push({ check: 'copy', detail: missingCopy });

      // element presence
      const missingEls = elements
        .filter((el) => el.el && !document.querySelector(`[data-el="${el.el}"]`))
        .map((el) => el.el);
      if (missingEls.length) violations.push({ check: 'elements', detail: missingEls });

      const invisibleSurfaceOwners = elements.flatMap((entry) => {
        if (!entry?.el || (!entry.surfaceIntegration && !['full-bleed', 'generated'].includes(entry.backgroundBehavior))) return [];
        const node = document.querySelector(`[data-el="${entry.el}"]`);
        if (!node) return [];
        const cs = getComputedStyle(node);
        const box = node.getBoundingClientRect();
        const opacity = Number(cs.opacity);
        const hiddenAncestor = (() => {
          for (let current = node.parentElement; current; current = current.parentElement) {
            const parentStyle = getComputedStyle(current);
            if (parentStyle.display === 'none' || parentStyle.visibility === 'hidden' ||
                parentStyle.contentVisibility === 'hidden' || Number(parentStyle.opacity) <= 0.01) {
              return current.tagName.toLowerCase();
            }
          }
          return null;
        })();
        const hidden = cs.display === 'none' || cs.visibility === 'hidden' ||
          cs.contentVisibility === 'hidden' || !Number.isFinite(opacity) || opacity <= 0.01 ||
          Boolean(hiddenAncestor) || box.width <= 0 || box.height <= 0;
        return hidden ? [{
          id: entry.id,
          el: entry.el,
          display: cs.display,
          visibility: cs.visibility,
          contentVisibility: cs.contentVisibility,
          opacity: cs.opacity,
          hiddenAncestor,
          rect: roundedBox({ width: box.width, height: box.height }),
        }] : [];
      });
      if (invisibleSurfaceOwners.length) {
        violations.push({
          check: 'surface-visible-owner',
          detail: {
            items: invisibleSurfaceOwners,
            instruction: 'Bind data-el to the visible img/picture/background owner that paints the adopted surface. Invisible duplicate DOM may not stand in for measurement.',
          },
        });
      }

      // A source-specific drawn icon, UI composite, or card device is not
      // preserved when its visible craft is replaced by a lone emoji or
      // Unicode dingbat. Audit leaf nodes so a legitimate text label on the
      // containing card does not hide the category stand-in.
      const standinSensitiveMedia = new Set(['line-art', 'illustration', 'ui', 'card-composite', 'decorative-geometry']);
      const symbolPattern = /(?:\p{Extended_Pictographic}|[\u2190-\u21ff\u2300-\u23ff\u2460-\u24ff\u25a0-\u27bf])/u;
      const symbolPatternGlobal = /(?:\p{Extended_Pictographic}|[\u2190-\u21ff\u2300-\u23ff\u2460-\u24ff\u25a0-\u27bf])/gu;
      for (const item of detailInventory || []) {
        const craft = item?.renderingCraft || {};
        if (
          item?.sourceSpecific !== true ||
          craft.genericStandInsForbidden !== true ||
          craft.allowTextGlyphStandIn === true ||
          !standinSensitiveMedia.has(craft.medium)
        ) continue;
        const found = [];
        for (const elementId of item.manifestElementIds || []) {
          const entry = byId[elementId];
          if (!entry?.el) continue;
          const host = document.querySelector(`[data-el="${entry.el}"]`);
          if (!host) continue;
          for (const node of [host, ...host.querySelectorAll('*')]) {
            if (node.children.length > 0) continue;
            const text = String(node.textContent || '').trim();
            if (!text || !symbolPattern.test(text)) continue;
            if (text.replace(symbolPatternGlobal, '').replace(/[\s\uFE0E\uFE0F]/g, '') !== '') continue;
            if (node.querySelector('img,svg,picture,canvas,video')) continue;
            found.push({
              elementId,
              node: node.tagName.toLowerCase(),
              text,
            });
          }
        }
        if (found.length) {
          violations.push({
            check: 'generic-symbol-standin',
            id: item.id,
            detail: {
              medium: craft.medium,
              signatureTraits: craft.signatureTraits || [],
              standins: found,
              instruction: 'Rebuild the source motif at its declared medium and atomic complexity; emoji/Unicode-symbol-only leaves are category stand-ins, not fidelity.',
            },
          });
        }
      }

      // layout law: flow elements should not secretly become
      // absolute/fixed/sticky unless the manifest explicitly declares the
      // matching positioning or the layer role is sanctioned for layering.
      const allowedAbsoluteRoles = new Set([
        'background-photo',
        'photo-overlay-gradient',
        'decorative-outline-type',
        'accent-band',
        'vertical-label',
        'badge',
        'decorative',
      ]);
      for (const node of document.querySelectorAll('[data-el]')) {
        const cs = getComputedStyle(node);
        if (!['absolute', 'fixed', 'sticky'].includes(cs.position)) continue;
        const entry = byEl[node.dataset.el] || {};
        if (entry.positioning === cs.position || allowedAbsoluteRoles.has(entry.layerRole)) continue;
        violations.push({
          check: 'layout-law',
          el: node.dataset.el,
          id: entry.id || null,
          detail: `computed position:${cs.position}; manifest positioning:${entry.positioning || 'flow'} layerRole:${entry.layerRole || 'none'}`,
        });
      }

      // Small decoration often carries more meaning than its area suggests.
      // Bind data-el to the primitive/group itself so the browser can reject
      // a stretched circle, a trapezoid standing in for a triangle, or rays
      // that begin inside a numeral instead of sitting outside it.
      for (const entry of elements) {
        const micro = entry.decorativeCraft?.microGeometry;
        if (!micro) continue;
        const host = document.querySelector(`[data-el="${entry.el}"]`);
        if (!host) continue;
        const hostRect = rectBox(host);
        if (micro.kind === 'circle') {
          const error = Math.abs(hostRect.width - hostRect.height) /
            Math.max(1, Math.max(hostRect.width, hostRect.height));
          if (error > micro.maxAspectRatioError) {
            violations.push({
              check: 'micro-geometry-circle', id: entry.id, el: entry.el,
              detail: { width: hostRect.width, height: hostRect.height,
                aspectRatioError: Math.round(error * 10000) / 10000,
                maxAspectRatioError: micro.maxAspectRatioError,
                instruction: 'Bind data-el to the circle primitive and give it a fixed/aspect-ratio:1 box with flex-shrink:0.' },
            });
          }
        } else if (micro.kind === 'triangle') {
          const polygon = host.matches('polygon') ? host : host.querySelector('polygon');
          let vertexCount = polygon?.points?.numberOfItems || 0;
          if (!vertexCount) {
            const clip = String(getComputedStyle(host).clipPath || '');
            const match = clip.match(/^polygon\((.*)\)$/i);
            vertexCount = match ? match[1].split(',').filter((part) => part.trim()).length : 0;
          }
          if (vertexCount !== micro.polygonVertexCount) {
            violations.push({
              check: 'micro-geometry-triangle', id: entry.id, el: entry.el,
              detail: { actualVertexCount: vertexCount,
                expectedVertexCount: micro.polygonVertexCount,
                instruction: 'Use an SVG polygon or clip-path polygon with exactly three measured vertices; do not leave a trapezoid.' },
            });
          }
        } else if (micro.kind === 'radial-rays') {
          const targetEntry = byId[micro.targetId];
          const target = targetEntry ? document.querySelector(`[data-el="${targetEntry.el}"]`) : null;
          let rays = [];
          try { rays = [...host.querySelectorAll(micro.raySelector)]; } catch {
            violations.push({ check: 'micro-geometry-radial-rays', id: entry.id, el: entry.el,
              detail: { instruction: `Invalid raySelector: ${micro.raySelector}` } });
            continue;
          }
          if (!target || rays.length !== micro.rayCount) {
            violations.push({
              check: 'micro-geometry-radial-rays', id: entry.id, el: entry.el,
              detail: { targetFound: Boolean(target), actualRayCount: rays.length,
                expectedRayCount: micro.rayCount },
            });
            continue;
          }
          const targetRect = rectBox(target);
          const targetCenter = {
            x: (targetRect.left + targetRect.right) / 2,
            y: (targetRect.top + targetRect.bottom) / 2,
          };
          const rayRows = rays.map((ray) => {
            const rect = rectBox(ray);
            return { ray, rect, center: { x: (rect.left + rect.right) / 2, y: (rect.top + rect.bottom) / 2 } };
          });
          const average = rayRows.reduce((sum, row) => ({
            x: sum.x + row.center.x / rayRows.length,
            y: sum.y + row.center.y / rayRows.length,
          }), { x: 0, y: 0 });
          const dx = average.x - targetCenter.x;
          const dy = average.y - targetCenter.y;
          const regionMatches = ({
            'upper-right': dx > 0 && dy < 0,
            'upper-left': dx < 0 && dy < 0,
            'lower-right': dx > 0 && dy > 0,
            'lower-left': dx < 0 && dy > 0,
            above: dy < 0,
            below: dy > 0,
            left: dx < 0,
            right: dx > 0,
          })[micro.placementRegion] === true;
          if (!regionMatches) {
            violations.push({
              check: 'micro-geometry-radial-placement', id: entry.id, el: entry.el,
              detail: { placementRegion: micro.placementRegion, offsetFromTargetCenter: { x: dx, y: dy } },
            });
          }
          if (micro.mustNotOverlapTarget) {
            for (const row of rayRows) {
              const rayBox = { x: row.rect.left, y: row.rect.top, w: row.rect.width, h: row.rect.height };
              const targetBox = { x: targetRect.left, y: targetRect.top, w: targetRect.width, h: targetRect.height };
              if (intersect(rayBox, targetBox) > 0) {
                violations.push({
                  check: 'micro-geometry-radial-overlap', id: entry.id, el: entry.el,
                  detail: { targetId: micro.targetId,
                    instruction: 'The numeral center is a direction reference, not the ray origin; move each ray outside the numeral.' },
                });
                break;
              }
            }
          }
          if (micro.directionMode === 'radiate-away') {
            const badDirections = [];
            for (const [index, row] of rayRows.entries()) {
              const cs = getComputedStyle(row.ray);
              const matrix = new DOMMatrixReadOnly(cs.transform === 'none' ? undefined : cs.transform);
              const localHorizontal = parseFloat(cs.width) >= parseFloat(cs.height);
              let axis = localHorizontal ? { x: matrix.a, y: matrix.b } : { x: matrix.c, y: matrix.d };
              const axisLength = Math.hypot(axis.x, axis.y) || 1;
              axis = { x: axis.x / axisLength, y: axis.y / axisLength };
              let radial = { x: row.center.x - targetCenter.x, y: row.center.y - targetCenter.y };
              const radialLength = Math.hypot(radial.x, radial.y) || 1;
              radial = { x: radial.x / radialLength, y: radial.y / radialLength };
              const dot = Math.min(1, Math.abs(axis.x * radial.x + axis.y * radial.y));
              const errorDeg = Math.acos(dot) * 180 / Math.PI;
              if (errorDeg > micro.maxDirectionErrorDeg) {
                badDirections.push({ index, errorDeg: Math.round(errorDeg * 10) / 10 });
              }
            }
            if (badDirections.length) {
              violations.push({
                check: 'micro-geometry-radial-direction', id: entry.id, el: entry.el,
                detail: { badDirections, maxDirectionErrorDeg: micro.maxDirectionErrorDeg },
              });
            }
          }
          if (micro.sharedOrigin === false && rayRows.length > 1) {
            let minSeparation = Infinity;
            for (let i = 0; i < rayRows.length; i++) {
              for (let j = i + 1; j < rayRows.length; j++) {
                minSeparation = Math.min(minSeparation, Math.hypot(
                  rayRows[i].center.x - rayRows[j].center.x,
                  rayRows[i].center.y - rayRows[j].center.y,
                ));
              }
            }
            if (minSeparation < micro.minRayCenterSeparationPx) {
              violations.push({
                check: 'micro-geometry-radial-origin', id: entry.id, el: entry.el,
                detail: { minRayCenterSeparationPx: minSeparation,
                  required: micro.minRayCenterSeparationPx,
                  instruction: 'Place ray centers along an invisible outer arc; do not make all bars share one point.' },
              });
            }
          }
        }
      }

      for (const entry of elements) {
        const contact = entry.surfaceIntegration?.edgeContact;
        if (!contact) continue;
        const art = document.querySelector(`[data-el="${entry.el}"]`);
        const ownerEntry = byId[contact.ownerId];
        const owner = ownerEntry ? document.querySelector(`[data-el="${ownerEntry.el}"]`) : null;
        if (!art || !owner) continue;
        const a = rectBox(art); const b = rectBox(owner);
        const gaps = {
          top: Math.abs(a.top - b.top), right: Math.abs(a.right - b.right),
          bottom: Math.abs(a.bottom - b.bottom), left: Math.abs(a.left - b.left),
        };
        const failed = contact.edges
          .filter((edge) => gaps[edge] > contact.maxGapPx)
          .map((edge) => ({ edge, gapPx: Math.round(gaps[edge] * 10) / 10 }));
        if (failed.length) {
          violations.push({
            check: 'surface-edge-contact', id: entry.id, el: entry.el,
            detail: { ownerId: contact.ownerId, failed, maxGapPx: contact.maxGapPx,
              instruction: 'Remove generic card padding from the artwork layer and position the caption independently.' },
          });
        }
      }

      if (strictHybrid) {
        for (const node of document.body.querySelectorAll('*')) {
          const cs = getComputedStyle(node);
          const text = String(node.textContent || '').trim().replace(/\s+/g, '');
          if (
            !node.hasAttribute('data-el') &&
            ['absolute', 'fixed', 'sticky'].includes(cs.position) &&
            text && text.length <= 12 &&
            parseFloat(cs.fontSize) >= Math.max(64, window.innerWidth * 0.05)
          ) {
            violations.push({
              check: 'unmanifested-large-text-decoration',
              detail: { node: node.tagName.toLowerCase(), className: node.className, text,
                instruction: 'Register large decorative lettering with data-el, layerRole, zLayer and mustStayBehind before styling.' },
            });
          }
        }

        for (const host of document.body.querySelectorAll('[data-el]')) {
          const entry = byEl[host.dataset.el] || {};
          for (const pseudo of ['::before', '::after']) {
            const cs = getComputedStyle(host, pseudo);
            if (!cs.content || ['none', 'normal'].includes(cs.content)) continue;
            const width = parseFloat(cs.width), height = parseFloat(cs.height);
            if (!Number.isFinite(width) || !Number.isFinite(height) || width * height < window.innerWidth * window.innerHeight * 0.04) continue;
            const rounded = String(cs.borderRadius).includes('50%');
            const ellipseRatio = Math.max(width, height) / Math.max(1, Math.min(width, height));
            const craft = entry.decorativeCraft || {};
            const evidencedEllipse = craft.geometryPrimitive === 'ellipse' && craft.ellipseException?.sourceEvidenced === true;
            if (rounded && ellipseRatio > 1.15 && !evidencedEllipse) {
              violations.push({
                check: 'unevidenced-large-ellipse', id: entry.id || null, el: host.dataset.el,
                detail: { pseudo, width, height, ellipseRatio: Math.round(ellipseRatio * 100) / 100,
                  instruction: 'Use a measured bezier or an off-canvas true circle (equal width/height); ellipse needs source-evidenced exception.' },
              });
            }
          }
        }
      }

      // Typography integrity: box convergence must not be purchased by
      // distorting or visually translating structural copy. Font choice,
      // font-size, weight, tracking, leading, run-level sizing, and optical
      // punctuation alignment are the normal repair controls.
      for (const entry of elements) {
        if (!structuralText(entry)) continue;
        const node = document.querySelector(`[data-el="${entry.el}"]`);
        if (!node) continue;
        const cs = getComputedStyle(node);
        const declaredFamily = String(entry.text?.fontFamily || '').replace(/["']/g, '').trim().toLowerCase();
        const renderedFamily = String(cs.fontFamily || '').replace(/["']/g, '').toLowerCase();
        if (declaredFamily && !renderedFamily.includes(declaredFamily)) {
          violations.push({
            check: 'font-family',
            id: entry.id,
            el: entry.el,
            detail: `rendered font-family '${cs.fontFamily}' does not contain frozen manifest family '${entry.text.fontFamily}'`,
          });
        }
        const fontSelection = entry.typeSpec?.fontSelection;
        if (fontSelection) {
          const selectedFamily = normalizedFontFamily(fontSelection.selectedFamily);
          const requestedWeight = fontWeightNumber(fontSelection.requestedWeight);
          const computedWeight = fontWeightNumber(cs.fontWeight);
          if (fontSelection.selectedSource !== 'system') {
            const loadedFace = deliveredFontFaces.some((face) =>
              face.family === selectedFamily &&
              face.status === 'loaded' &&
              requestedWeight !== null &&
              requestedWeight >= face.minWeight &&
              requestedWeight <= face.maxWeight
            );
            if (!loadedFace) {
              violations.push({
                check: 'font-face-load', id: entry.id, el: entry.el,
                detail: {
                  selectedFamily: fontSelection.selectedFamily,
                  selectedSource: fontSelection.selectedSource,
                  requestedWeight,
                  computedFamily: cs.fontFamily,
                  deliveredFaces: deliveredFontFaces.filter((face) => face.family === selectedFamily),
                  instruction: 'Load the chosen webfont face before fidelity QA; a family string that silently falls back is not a typography match.',
                },
              });
            }
          }
          if (requestedWeight !== null && computedWeight !== null && Math.abs(computedWeight - requestedWeight) > 1) {
            violations.push({
              check: 'font-weight-face', id: entry.id, el: entry.el,
              detail: {
                requestedWeight,
                computedWeight,
                availableWeights: fontSelection.availableWeights || [],
                variableWeightRange: fontSelection.variableWeightRange || null,
                instruction: 'Deliver and apply the measured role weight; do not let the browser synthesize or downgrade it.',
              },
            });
          }
        }
        const expectedLineCount = entry.typeSpec?.expectedVisualLineCount;
        if (entry.qaPriority === 'fv-critical' &&
            Number.isInteger(expectedLineCount) && expectedLineCount > 0 &&
            Number.isFinite(canonicalWidth) && Math.abs(window.innerWidth - canonicalWidth) <= 1) {
          const actualLineCount = renderedLineCount(node);
          if (actualLineCount !== expectedLineCount) {
            violations.push({
              check: 'typography-line-count',
              id: entry.id,
              el: entry.el,
              detail: {
                expected: expectedLineCount,
                actual: actualLineCount,
                viewportWidth: window.innerWidth,
                instruction: 'Restore the comp-measured lockup line count with container width, font metrics, tracking and flow spacing; do not accept an accidental wrap that changes lockup height.',
              },
            });
          }
        }
        const lineContract = (entry.typeSpec?.responsiveLineContracts || []).find((contract) =>
          Number.isFinite(contract?.minWidth) && Number.isFinite(contract?.maxWidth) &&
          window.innerWidth >= contract.minWidth && window.innerWidth <= contract.maxWidth
        );
        if (lineContract) {
          const actualLines = renderedLineStrings(node).map(norm);
          const expectedLines = (lineContract.expectedLines || []).map(norm);
          const orphanFragments = (lineContract.forbiddenOrphanFragments || []).map(norm).filter(Boolean);
          const foundOrphans = actualLines.filter((line) => orphanFragments.includes(line));
          if (actualLines.length !== expectedLines.length || actualLines.some((line, index) => line !== expectedLines[index])) {
            violations.push({
              check: 'typography-responsive-lines', id: entry.id, el: entry.el,
              detail: { expectedLines, actualLines, viewportWidth: window.innerWidth,
                instruction: 'Preserve semantic Japanese line strings with line spans/container width/font metrics; do not strand an inflection or particle.' },
            });
          }
          if (foundOrphans.length) {
            violations.push({
              check: 'typography-orphan-fragment', id: entry.id, el: entry.el,
              detail: { fragments: foundOrphans, actualLines, viewportWidth: window.innerWidth },
            });
          }
        }
        if (!cs.transform || cs.transform === 'none') continue;
        const matrix = new DOMMatrixReadOnly(cs.transform);
        const scaleX = Math.hypot(matrix.a, matrix.b);
        const scaleY = Math.hypot(matrix.c, matrix.d);
        const axisDot = scaleX && scaleY
          ? Math.abs((matrix.a * matrix.c + matrix.b * matrix.d) / (scaleX * scaleY))
          : 0;
        const distorted = (
          Math.abs(scaleX - 1) > 0.02 ||
          Math.abs(scaleY - 1) > 0.02 ||
          Math.abs(scaleX - scaleY) > 0.015 ||
          axisDot > 0.01 ||
          Math.abs(matrix.b) > 0.01 ||
          Math.abs(matrix.c) > 0.01
        );
        const translated = Math.abs(matrix.e) > 0.5 || Math.abs(matrix.f) > 0.5;
        if ((distorted || translated) && !transformExceptionValid(entry)) {
          violations.push({
            check: 'typography-transform',
            id: entry.id,
            el: entry.el,
            detail: {
              transform: cs.transform,
              scaleX: Math.round(scaleX * 1000) / 1000,
              scaleY: Math.round(scaleY * 1000) / 1000,
              translateX: Math.round(matrix.e * 10) / 10,
              translateY: Math.round(matrix.f * 10) / 10,
              instruction: 'Repair with a class-matched font, size, weight, tracking, leading, run-level sizing, or flow spacing; do not distort/translate structural text to pass box diff.',
            },
          });
        }
      }

      // Typography is a section-wide composition. Checking each text box in
      // isolation still permits the common failure where display, card titles,
      // labels, and microcopy all converge on one safe middle size/weight.
      for (const composition of typographyComposition || []) {
        const dominantEntry = byId[composition.dominantElementId];
        const dominantNode = dominantEntry?.el
          ? document.querySelector(`[data-el="${dominantEntry.el}"]`)
          : null;
        const dominantRect = dominantNode?.getBoundingClientRect();
        for (const edge of composition.hierarchyEdges || []) {
          const fromEntry = byId[edge.from];
          const toEntry = byId[edge.to];
          const fromNode = fromEntry?.el ? document.querySelector(`[data-el="${fromEntry.el}"]`) : null;
          const toNode = toEntry?.el ? document.querySelector(`[data-el="${toEntry.el}"]`) : null;
          if (!fromNode || !toNode) continue;
          const fromStyle = getComputedStyle(fromNode);
          const toStyle = getComputedStyle(toNode);
          const fromSize = Number.parseFloat(fromStyle.fontSize);
          const toSize = Number.parseFloat(toStyle.fontSize);
          const fromWeight = fontWeightNumber(fromStyle.fontWeight);
          const toWeight = fontWeightNumber(toStyle.fontWeight);
          const actualSizeRatio = fromSize / Math.max(0.01, toSize);
          const actualWeightDelta = fromWeight !== null && toWeight !== null ? fromWeight - toWeight : null;
          const sizeAllowed = Math.max(0.04, Math.abs(edge.sourceSizeRatio) * edge.sizeTolerance);
          const sizeDrift = Math.abs(actualSizeRatio - edge.sourceSizeRatio);
          const weightDrift = actualWeightDelta === null ? Infinity : Math.abs(actualWeightDelta - edge.sourceWeightDelta);
          if (sizeDrift > sizeAllowed || weightDrift > edge.weightTolerance) {
            violations.push({
              check: 'typography-hierarchy',
              id: `${edge.from}->${edge.to}`,
              detail: {
                sourceSizeRatio: edge.sourceSizeRatio,
                actualSizeRatio: Math.round(actualSizeRatio * 1000) / 1000,
                sizeTolerance: edge.sizeTolerance,
                sourceWeightDelta: edge.sourceWeightDelta,
                actualWeightDelta,
                weightTolerance: edge.weightTolerance,
                instruction: 'Restore the comp hierarchy with role-specific family/weight/size; do not normalize all copy into one safe scale.',
              },
            });
          }
        }
        for (const edge of composition.whitespaceEdges || []) {
          const beforeEntry = byId[edge.before];
          const afterEntry = byId[edge.after];
          const beforeNode = beforeEntry?.el ? document.querySelector(`[data-el="${beforeEntry.el}"]`) : null;
          const afterNode = afterEntry?.el ? document.querySelector(`[data-el="${afterEntry.el}"]`) : null;
          if (!beforeNode || !afterNode || !dominantRect?.height) continue;
          const beforeRect = beforeNode.getBoundingClientRect();
          const afterRect = afterNode.getBoundingClientRect();
          const actualGap = afterRect.top - beforeRect.bottom;
          const actualRatio = actualGap / dominantRect.height;
          if (Math.abs(actualRatio - edge.sourceGapToDominantRatio) > edge.tolerance) {
            violations.push({
              check: 'typography-whitespace',
              id: `${edge.before}->${edge.after}`,
              detail: {
                sourceGapToDominantRatio: edge.sourceGapToDominantRatio,
                actualGapToDominantRatio: Math.round(actualRatio * 1000) / 1000,
                actualGapPx: Math.round(actualGap * 10) / 10,
                tolerance: edge.tolerance,
                instruction: 'Tune measured block spacing and line-height; negative space is part of the typography, not leftover section padding.',
              },
            });
          }
        }
        const extreme = composition.extremeScale;
        if (
          extreme?.required === true && dominantRect?.height &&
          Number.isFinite(canonicalWidth) && Math.abs(window.innerWidth - canonicalWidth) <= 1
        ) {
          const actualRatio = dominantRect.height / window.innerHeight;
          const minimumRatio = extreme.sourceDominantBlockHeightRatio * (1 - extreme.maxScaleLossRatio);
          if (actualRatio < minimumRatio) {
            violations.push({
              check: 'typography-extreme-scale', id: composition.dominantElementId,
              detail: {
                sourceDominantBlockHeightRatio: extreme.sourceDominantBlockHeightRatio,
                maxScaleLossRatio: extreme.maxScaleLossRatio,
                minimumRatio: Math.round(minimumRatio * 10000) / 10000,
                actualRatio: Math.round(actualRatio * 10000) / 10000,
                instruction: 'Do not cap the display role into a tasteful middle size. Preserve the source poster-scale footprint and rebalance surrounding whitespace.',
              },
            });
          }
        }
      }

      // A gradient/photo/veil declared inside a rounded frame must actually be
      // clipped by that owner. Otherwise an element-local treatment can become
      // the page-wide wash seen in failed reproductions.
      for (const entry of elements) {
        if (!entry.clipOwner) continue;
        const ownerEntry = byId[entry.clipOwner] || byEl[entry.clipOwner];
        const owner = ownerEntry?.el
          ? document.querySelector(`[data-el="${ownerEntry.el}"]`)
          : document.querySelector(`[data-el="${entry.clipOwner}"]`);
        if (!owner) {
          violations.push({
            check: 'clip-owner',
            id: entry.id,
            el: entry.el,
            detail: `declared clipOwner '${entry.clipOwner}' is missing from the DOM/manifest`,
          });
          continue;
        }
        const ownerStyle = getComputedStyle(owner);
        const clipsOverflow = ['hidden', 'clip'].includes(ownerStyle.overflowX) &&
          ['hidden', 'clip'].includes(ownerStyle.overflowY);
        const hasShapeClip = Boolean(
          (ownerStyle.clipPath && ownerStyle.clipPath !== 'none') ||
          (ownerStyle.maskImage && ownerStyle.maskImage !== 'none')
        );
        if (!clipsOverflow && !hasShapeClip) {
          violations.push({
            check: 'clip-owner',
            id: entry.id,
            el: entry.el,
            detail: `clipOwner '${entry.clipOwner}' does not clip overflow or define clip-path/mask-image`,
          });
        }
      }

      // FV background layer intent
      for (const el of elements) {
        if (!['full-bleed', 'generated'].includes(el.backgroundBehavior)) continue;
        const r = rectOf(el.el);
        if (!r) continue;
        const cs = getComputedStyle(r.e);
        const problems = [];
        if (!['absolute', 'fixed'].includes(cs.position)) problems.push(`position:${cs.position} (expected absolute/fixed layer)`);
        if (r.w < window.innerWidth * 0.98) problems.push(`width ${Math.round(r.w)} < 98% of viewport (looks like a framed card, not a background)`);
        if (problems.length) violations.push({ check: 'fv-layer', id: el.id, detail: problems });
      }

      // declared mustNotCover
      for (const el of elements) {
        for (const otherId of el.mustNotCover || []) {
          const other = byId[otherId];
          if (!other) continue;
          const a = rectOf(el.el); const b = rectOf(other.el);
          if (a && b && intersect(a, b) > 0) {
            violations.push({ check: 'must-not-cover', detail: `${el.id} covers ${otherId}` });
          }
        }
      }
      for (const el of elements) {
        for (const otherId of el.mustStayBehind || []) {
          const other = byId[otherId];
          if (!other) continue;
          const a = rectOf(el.el); const b = rectOf(other.el);
          if (!a || !b || intersect(a, b) <= 0) continue;
          const aZ = Number.parseInt(getComputedStyle(a.e).zIndex, 10);
          const bZ = Number.parseInt(getComputedStyle(b.e).zIndex, 10);
          const sourceZ = Number.isFinite(aZ) ? aZ : 0;
          const targetZ = Number.isFinite(bZ) ? bZ : 0;
          if (sourceZ >= targetZ) {
            violations.push({
              check: 'must-stay-behind', id: el.id, el: el.el,
              detail: `${el.id} z-index ${sourceZ} is not behind ${otherId} z-index ${targetZ}`,
            });
          }
        }
      }

      // Undeclared structural-text overlaps are hard failures. Decorative or
      // non-structural overlaps remain warnings because overlap may be the design.
      const textEls = elements.filter((el) => el.text?.content || ['heading', 'text', 'label', 'button'].includes(el.role));
      for (let i = 0; i < textEls.length; i++) {
        for (let j = i + 1; j < textEls.length; j++) {
          const A = textEls[i], B = textEls[j];
          const declared = (A.overlaps || []).includes(B.id) || (B.overlaps || []).includes(A.id);
          if (declared) continue;
          const aNode = document.querySelector(`[data-el="${A.el}"]`);
          const bNode = document.querySelector(`[data-el="${B.el}"]`);
          if (aNode && bNode && (aNode.contains(bNode) || bNode.contains(aNode))) continue;
          const a = rectOf(A.el), b = rectOf(B.el);
          if (!a || !b) continue;
          const ov = intersect(a, b);
          if (ov > 0.15 * Math.min(a.w * a.h, b.w * b.h)) {
            const detail = `${A.id} × ${B.id} intersect without declared overlaps/overlapIntent`;
            if (structuralText(A) && structuralText(B)) {
              violations.push({ check: 'text-overlap', detail });
            } else {
              warnings.push({ check: 'overlap-candidate', detail });
            }
          }
        }
      }

      // mobile-specific
      if (isMobile) {
        for (const el of elements) {
          if (el.qaPriority !== 'fv-critical') continue;
          const r = rectOf(el.el);
          if (!r) continue;
          const cs = getComputedStyle(r.e);
          if (el.role === 'heading' && parseFloat(cs.fontSize) < minHeadingPx) {
            violations.push({ check: 'mobile-heading-size', id: el.id, detail: `${cs.fontSize} < ${minHeadingPx}px — hero heading loses the poster on SP` });
          }
          if ((el.role === 'button' || el.layerRole === 'cta') &&
              (r.w === 0 || r.h === 0 || cs.visibility === 'hidden' || cs.display === 'none')) {
            violations.push({ check: 'mobile-cta-visible', id: el.id, detail: 'CTA not visible on mobile' });
          }
        }
      }
      return { violations, warnings, responsiveMetrics };
    }, {
      elements: manifest.elements || [],
      detailInventory: manifest.detailInventory || [],
      typographyComposition: manifest.typographyComposition || [],
      sectionEls,
      pageSectionContracts,
      minHeadingPx,
      isMobile: vw < 768,
      runDeadGutter: widthMode,
      canonicalWidth: Number(manifest.viewport?.width),
      strictHybrid,
    });

    if (!pipelineContract.pass) {
      r.violations.unshift({
        check: 'pipeline-pre-css-contract',
        detail: {
          ...pipelineContract,
          instruction: 'Responsive/intent QA cannot pass a hybrid multi-frame run until hash-bound contract-doctor and asset-preflight reports authorize implementation.',
        },
      });
    }
    if (failedRequests.length) r.violations.push({ check: 'requests', detail: failedRequests });
    results.push({ viewport: `${vw}x${vh}`, pass: r.violations.length === 0, ...r });
    await page.close();
  }
} finally {
  await browser.close();
}

const report = {
  ok: results.every((r) => r.pass),
  browser: executable,
  html: args.html || args.url,
  manifest: args.manifest || null,
  pipelineContract,
  widthMode,
  viewports: results,
};
const text = JSON.stringify(report, null, 2);
if (args.out) {
  await mkdir(dirname(resolve(args.out)), { recursive: true });
  await writeFile(args.out, text);
}
console.log(text);
process.exit(report.ok ? 0 : 1);
