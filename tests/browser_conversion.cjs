#!/usr/bin/env node
'use strict';
/**
 * Exercise the actual static app and Genesis 2 regression page in Chromium.
 * node tests/browser_conversion.cjs http://127.0.0.1:8000/ \
 *   --report work/browser.json --screenshot work/genesis2.png
 * Start the static server separately. This script never changes site data.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const [baseArg, ...flags] = process.argv.slice(2);
if (!baseArg || flags.length % 2) {
  process.stderr.write('Usage: node tests/browser_conversion.cjs BASE_URL [--report FILE] [--screenshot FILE] [--chromium FILE]\n');
  process.exit(2);
}
const options = {};
for (let i = 0; i < flags.length; i += 2) {
  if (!['--report', '--screenshot', '--chromium'].includes(flags[i])) {
    throw new Error('Unknown option ' + flags[i]);
  }
  options[flags[i].slice(2)] = flags[i + 1];
}
const base = new URL(baseArg);
if (!['http:', 'https:'].includes(base.protocol)) throw new Error('BASE_URL must be HTTP(S)');
base.hash = '';
base.search = '';
if (!base.pathname.endsWith('/')) base.pathname += '/';

const originalLinks = [
  [33, 1, 'Eden'], [33, 1, 'Eden'], [34, 1, 'Eden'], [35, 2, 'Pison'],
  [35, 3, 'Chawila '], [35, 3, 'I'], [36, 4, 'Gichon'], [36, 5, 'Ethiopie'],
  [37, 6, 'Tigris'], [37, 7, 'Assur'], [37, 8, 'Eufraat'], [38, 1, 'Eden'],
  [44, 0, 'Adam'],
];
const originalRecords = [
  ['Adam', 'persoon', 'waarschijnlijk'], ['Eden', 'plaats', 'zeker'],
  ['Pison', 'water', 'waarschijnlijk'], ['Chawila I', 'persoon', 'waarschijnlijk'],
  ['Gichon', 'water', 'zeker'], ['Ethiopie', 'land', 'waarschijnlijk'],
  ['Tigris', 'water', 'waarschijnlijk'], ['Assur', 'land', 'zeker'],
  ['Eufraat', 'water', 'zeker'],
];
const report = { base_url: base.href, passed: false, checks: [], page_errors: [], failed_local_requests: [] };
let browser;

async function check(name, run) {
  const started = Date.now();
  try {
    const detail = await run();
    report.checks.push({ name, passed: true, duration_ms: Date.now() - started, ...(detail ? { detail } : {}) });
    process.stdout.write('PASS ' + name + '\n');
  } catch (error) {
    report.checks.push({ name, passed: false, duration_ms: Date.now() - started, error: error.message });
    throw error;
  }
}

async function main() {
  browser = await chromium.launch({ executablePath: options.chromium || '/usr/bin/chromium', headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const context = await browser.newContext({ viewport: { width: 1365, height: 1000 } });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => report.page_errors.push(error.message));
  page.on('response', response => {
    const url = new URL(response.url());
    if (url.origin === base.origin && response.status() >= 400 && !url.pathname.endsWith('/favicon.ico')) {
      report.failed_local_requests.push({ url: response.url(), status: response.status() });
    }
  });
  async function route(hash) {
    await page.goto(new URL(hash, base).href, { waitUntil: 'load' });
  }
  async function waitRead(book, chapter) {
    await page.waitForFunction(({ book, chapter }) => {
      const element = document.querySelector('#app h1');
      return window.SBW && SBW.meta && element && element.textContent === SBW.meta.books[book][0] + ' ' + chapter
        && document.querySelector('#selB')?.value === String(book)
        && document.querySelector('#selC')?.value === String(chapter);
    }, { book, chapter });
  }
  async function panelRecord(entity) {
    const [name, category, certainty] = originalRecords[entity];
    await page.waitForFunction(name => document.querySelector('#panel .p-name')?.textContent === name, name);
    assert.equal(await page.locator('#panel').isVisible(), true);
    assert.equal(await page.locator('#panel .p-name').textContent(), name);
    const badges = await page.locator('#panel .badges .badge').allTextContents();
    assert.deepEqual(badges.slice(0, 2), [category, certainty]);
    assert.equal(await page.evaluate(id => SBW.ents[id]?.n, entity), name);
    await page.locator('#panelClose').click();
    assert.equal(await page.locator('#panel').isVisible(), false);
  }

  await check('Genesis 2: 18 echte tekstblokken en 13 oorspronkelijke naamsegmenten', async () => {
    await route('#/lees/0/2');
    await waitRead(0, 2);
    assert.equal(await page.locator('#app .blk').count(), 18);
    const actual = await page.locator('#app .blk .ent').evaluateAll(elements => elements.map(element => [
      Number(element.closest('.blk').id.slice(1)), Number(element.dataset.e), element.textContent,
    ]));
    assert.deepEqual(actual, originalLinks);
    return { blocks: 18, linked_segments: actual.length };
  });

  await check('Genesis 2: alle tekstregels en CSS-kleuren/opmaak worden werkelijk gerenderd', async () => {
    const result = await page.evaluate(() => {
      const errors = [], properties = ['color', 'backgroundColor', 'fontWeight', 'fontStyle', 'textDecorationLine', 'textDecorationColor', 'fontFamily', 'fontSize', 'verticalAlign'];
      let rows = 0, segments = 0;
      const book = SBW.books[0], ids = book.ch['2'];
      for (const id of ids) {
        const block = book.bl[id], element = document.getElementById('b' + id);
        const sets = [{ source: [...(block.r || []), ...block.x], elements: [...element.children] }];
        if (Array.isArray(block.pre)) {
          const preceding = [];
          let previous = element.previousElementSibling;
          for (let n = 0; n < block.pre.length; n++) {
            if (previous) { preceding.unshift(previous); previous = previous.previousElementSibling; }
          }
          sets.push({ source: block.pre, elements: preceding });
        }
        for (const set of sets) {
        const expectedRows = set.source.filter(row => Array.isArray(row));
        const actualRows = set.elements.filter(e => e.classList.contains('ln'));
        if (expectedRows.length !== actualRows.length) errors.push('Wrong line count in block ' + id);
        for (let line = 0; line < expectedRows.length; line++) {
          rows++;
          const actualSegments = [...(actualRows[line]?.querySelectorAll('.x') || [])];
          if (actualSegments.length !== expectedRows[line].length) errors.push('Wrong segment count in block ' + id);
          for (let s = 0; s < expectedRows[line].length; s++) {
            segments++;
            const [text, style] = expectedRows[line][s], actual = actualSegments[s];
            const expectedText = s === 0 ? text.replace(/^\t+/, '') : text;
            if (!actual || actual.textContent !== expectedText) { errors.push('Text mismatch in block ' + id); continue; }
            const probe = document.createElement('span');
            probe.className = 'x';
            probe.style.cssText = SBW.meta.sty[style];
            actual.parentNode.append(probe);
            const expectedStyle = getComputedStyle(probe), actualStyle = getComputedStyle(actual);
            for (const property of properties) {
              if (expectedStyle[property] !== actualStyle[property]) errors.push('Style mismatch ' + property + ' in block ' + id);
            }
            for (const reference of actual.querySelectorAll('a.ref')) {
              if (getComputedStyle(reference).color !== actualStyle.color) errors.push('Reference overrode source color in block ' + id);
            }
            probe.remove();
          }
        }
        const gaps = set.source.filter(row => !row).length;
        if (set.elements.filter(e => e.classList.contains('gap')).length !== gaps) errors.push('Wrong blank-line count in block ' + id);
        }
      }
      return { rows, segments, errors };
    });
    assert.deepEqual(result.errors, []);
    assert.ok(result.rows > 18 && result.segments > 13);
    return result;
  });

  await check('Genesis 2: alle 13 namen openen het juiste echte wikirecord', async () => {
    for (let i = 0; i < originalLinks.length; i++) {
      await page.locator('#app .blk .ent').nth(i).click();
      await panelRecord(originalLinks[i][1]);
    }
    return { opened: originalLinks.length, eden: 'plaats / zeker', chawila: 'Chawila I / persoon / waarschijnlijk' };
  });

  await check('Naamkoppeling werkt ook met toetsenbord en Escape', async () => {
    const first = page.locator('#app .blk .ent').first();
    await first.focus();
    await first.press('Enter');
    await page.waitForFunction(() => document.querySelector('#panel .p-name')?.textContent === 'Eden');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#panel').isVisible(), false);
  });

  await check('Kleuren uitschakelen en herstellen verandert de tekst en links niet', async () => {
    const before = await page.locator('#app .txt .x').evaluateAll(elements => elements.map(e => [
      e.textContent, getComputedStyle(e).color, getComputedStyle(e).backgroundColor,
      getComputedStyle(e).fontWeight, getComputedStyle(e).fontStyle, getComputedStyle(e).textDecorationLine,
    ]));
    assert.ok(new Set(before.map(x => x[1])).size > 1, 'Expected several source colors in Genesis 2');
    await page.locator('#kleur').click();
    assert.equal(await page.locator('#app .txt').evaluate(e => e.classList.contains('plain')), true);
    const off = await page.locator('#app .txt .x').evaluateAll(elements => elements.map(e => [
      e.textContent, getComputedStyle(e).color, getComputedStyle(e).backgroundColor,
    ]));
    assert.equal(new Set(off.map(x => x[1])).size, 1);
    assert.ok(off.every(x => x[2] === 'rgba(0, 0, 0, 0)'));
    assert.deepEqual(off.map(x => x[0]), before.map(x => x[0]));
    assert.equal(await page.evaluate(() => localStorage.getItem('sbw-kleur')), 'uit');
    await page.locator('#kleur').click();
    const after = await page.locator('#app .txt .x').evaluateAll(elements => elements.map(e => [
      e.textContent, getComputedStyle(e).color, getComputedStyle(e).backgroundColor,
      getComputedStyle(e).fontWeight, getComputedStyle(e).fontStyle, getComputedStyle(e).textDecorationLine,
    ]));
    assert.deepEqual(after, before);
    assert.equal(await page.locator('#app .blk .ent').count(), 13);
    if (options.screenshot) {
      fs.mkdirSync(path.dirname(options.screenshot), { recursive: true });
      await page.screenshot({ path: options.screenshot, fullPage: true });
    }
    return { distinct_source_colors: new Set(before.map(x => x[1])).size };
  });

  await check('Hoofdstukkeuze en vorige/volgende hoofdstuk werken', async () => {
    await page.locator('#selC').selectOption('3');
    await waitRead(0, 3);
    assert.ok(await page.locator('#app .blk').count() > 0);
    await page.locator('#app .pager a').first().click();
    await waitRead(0, 2);
    assert.equal(await page.locator('#app .blk').count(), 18);
    await page.locator('#app .pager a').last().click();
    await waitRead(0, 3);
  });

  await check('Alle 66 boeken laden tekst en geldige naamkoppelingen', async () => {
    const samples = [];
    const bookCount = await page.evaluate(() => SBW.meta.books.length);
    assert.equal(bookCount, 66);
    for (let book = 0; book < bookCount; book++) {
      await page.locator('#selB').selectOption(String(book));
      const chapter = await page.evaluate(book => SBW.meta.books[book][1][0], book);
      await waitRead(book, chapter);
      const summary = await page.evaluate(({ book, chapter }) => {
        const ids = SBW.books[book].ch[chapter];
        return { name: SBW.meta.books[book][0], chapter, expected_blocks: ids.length,
          actual_blocks: document.querySelectorAll('#app .blk').length,
          text: [...document.querySelectorAll('#app .ln')].map(e => e.textContent).join('').length,
          broken_links: [...document.querySelectorAll('#app .ent')].filter(e => !SBW.meta.ents[Number(e.dataset.e)]).length };
      }, { book, chapter });
      assert.equal(summary.actual_blocks, summary.expected_blocks);
      assert.ok(summary.text > 0);
      assert.equal(summary.broken_links, 0);
      samples.push(summary);
    }
    return samples;
  });

  if (await page.evaluate(() => (SBW.meta.conversion?.converted_blocks || 0) > 17402)) {
    await check('Alle 18 aangevulde Deuteronomium-hoofdstukken hebben eigen leesroutes', async () => {
      const chapters = [6, 7, 8, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 26, 28];
      await page.locator('#selB').selectOption('4');
      await waitRead(4, 1);
      const summaries = [];
      for (const chapter of chapters) {
        await page.locator('#selC').selectOption(String(chapter));
        await waitRead(4, chapter);
        const summary = await page.evaluate(chapter => ({
          chapter, expected: SBW.books[4].ch[chapter].length,
          rendered: document.querySelectorAll('#app .blk').length,
          own_metadata: SBW.books[4].ch[chapter].every(id => SBW.meta.blk[id][0] === 4 && SBW.meta.blk[id][1] === chapter),
          text: [...document.querySelectorAll('#app .ln')].map(e => e.textContent).join('').length,
        }), chapter);
        assert.ok(summary.expected > 0);
        assert.equal(summary.rendered, summary.expected);
        assert.equal(summary.own_metadata, true);
        assert.ok(summary.text > 0);
        summaries.push(summary);
      }
      return summaries;
    });
  }

  await check('Wiki zoeken, categorie plaats en vaste Eden-link blijven bruikbaar', async () => {
    await route('#/wiki/O');
    await page.locator('#q').waitFor();
    assert.equal(await page.locator('#list [data-e="1"]').count(), 1);
    await page.locator('#q').fill('Eden');
    await page.locator('#list [data-e="1"]').click();
    await panelRecord(1);
    await route('#/e/1');
    await panelRecord(1);
  });

  await check('Legenda en informatiescherm worden geladen', async () => {
    await route('#/legenda');
    await page.locator('#app .legenda').waitFor();
    assert.ok(await page.locator('#app table.lg tr').count() > 40);
    assert.match(await page.locator('#app').textContent(), /Magenta tekst/);
    await route('#/over');
    await page.waitForFunction(() => document.querySelector('#app h1')?.textContent === 'Over deze wiki');
    const blockCount = await page.evaluate(() => SBW.meta.blk.length);
    assert.ok(blockCount >= 17402, 'Original block identities must remain present');
    assert.ok((await page.locator('#app').textContent()).includes(String(blockCount)));
    assert.match(await page.locator('#app').textContent(), /2808/);
  });

  if (await page.evaluate(() => Boolean(SBW.meta.conversion))) {
    await check('Voorwerk uit de RTF is bereikbaar en behoudt tekst bij kleurwissel', async () => {
      await page.locator('#app a[href="#/bron"]').click();
      await page.waitForFunction(() => SBW.rtfExtra && document.querySelector('#app h1')?.textContent === SBW.rtfExtra.title);
      const rendered = await page.evaluate(() => ({
        expected: SBW.rtfExtra.rows.filter(Array.isArray).map(row => row.map(s => s[0]).join('').replace(/^\t+/, '')),
        actual: [...document.querySelectorAll('#app .ln')].map(e => e.textContent),
        expectedGaps: SBW.rtfExtra.rows.filter(row => !row).length,
        actualGaps: document.querySelectorAll('#app .gap').length,
      }));
      assert.deepEqual(rendered.actual, rendered.expected);
      assert.equal(rendered.actualGaps, rendered.expectedGaps);
      await page.locator('#kleur').click();
      assert.equal(await page.locator('#app .txt').evaluate(e => e.classList.contains('plain')), true);
      assert.deepEqual(await page.locator('#app .ln').allTextContents(), rendered.expected);
      await page.locator('#kleur').click();
      assert.equal(await page.locator('#app .txt').evaluate(e => e.classList.contains('plain')), false);
      return { source_rows: rendered.expected.length + rendered.expectedGaps };
    });
  }

  await check('Bestaande Genesis 2 RTF-regressiepagina slaagt en opent echte Eden-data', async () => {
    await page.goto(new URL('tests/genesis2-rtf-regressie.html', base).href, { waitUntil: 'load' });
    await page.waitForFunction(() => document.querySelector('#status')?.classList.contains('ok') ||
      document.querySelector('#status')?.classList.contains('fail'));
    assert.equal(await page.locator('#status').evaluate(e => e.classList.contains('ok')), true,
      await page.locator('#status').textContent());
    assert.equal(await page.locator('#checks .fail').count(), 0);
    assert.equal(await page.locator('#checks .ok').count(), 4);
    assert.equal(await page.locator('#blocks article').count(), 18);
    assert.equal(await page.locator('#blocks .entity').count(), 13);
    await page.locator('#blocks .entity').first().click();
    await page.waitForFunction(() => document.querySelector('#who')?.textContent === 'Eden · plaats · zeker');
    assert.equal(await page.locator('#details').isVisible(), true);
    await page.locator('#close').click();
    assert.equal(await page.locator('#details').isVisible(), false);
  });

  await check('Geen JavaScript-fouten of ontbrekende lokale bestanden', async () => {
    assert.deepEqual(report.page_errors, []);
    assert.deepEqual(report.failed_local_requests, []);
  });
  report.passed = true;
}

main().catch(error => {
  report.error = error.stack || error.message;
  process.stderr.write(report.error + '\n');
  process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  if (options.report) {
    fs.mkdirSync(path.dirname(options.report), { recursive: true });
    fs.writeFileSync(options.report, JSON.stringify(report, null, 2) + '\n');
  }
  process.stdout.write(JSON.stringify({ passed: report.passed, checks: report.checks.length,
    report: options.report || null, screenshot: options.screenshot || null }) + '\n');
});
