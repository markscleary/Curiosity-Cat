// Tests for the explanation layer's pure core (app/src/js/territory-map.js,
// APP-T1): the PROFILE.md parser, the territory diagram SVG builder, and
// the what/from-what/since-when explain block.
// Run with: node --test tests/js
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const territory = require('../../app/src/js/territory-map.js');

// Structurally matches build_profile_md()'s output shape (curiosity_cat/
// core.py) for a housecat/claude-code profile — same headings, same bullet
// syntax, including the nested "Fetch pages only from:" sub-bullets.
const HOUSECAT_PROFILE_MD = [
  '# Curiosity Cat — Housecat profile (claude-code)',
  '',
  '*Cautious. Stay close to home. Standing orders followed. Nothing leaves the yard.*',
  '',
  '## What this cat can do',
  '',
  '- Read files inside this project.',
  '- Write and edit files inside this project.',
  '- Fetch pages only from:',
  '  - docs.anthropic.com',
  '  - docs.python.org',
  '',
  '## What this cat cannot do, no matter what',
  '',
  '- Read SSH keys, AWS credentials, `.env` files, `.pem` files, or anything with "credentials" in the name.',
  '- Run `sudo` or `rm -rf`.',
  '- Fetch a web page outside the allowlist above.',
  '- Write or edit a file outside this project.',
  '',
  '## The safety net underneath',
  '',
  '- Sandbox: on. This wraps Bash commands only.',
  '- Default permission mode: `default`.',
  '',
  'This profile was compiled, not hand-written.',
  ''
].join('\n');

const ALLEYCAT_PROFILE_MD_ASK_SECTION = [
  '# Curiosity Cat — Alley Cat profile (claude-code)',
  '',
  '*Balanced. Calculated risks accepted. Braver exploration. Still comes home.*',
  '',
  '## What this cat can do',
  '',
  '- Read files anywhere on this machine.',
  '- Write and edit files inside this project.',
  '- Fetch pages only from:',
  '  - github.com',
  '',
  '## What this cat has to ask about first',
  '',
  '- `curl`',
  '- `npm install`',
  '',
  '## What this cat cannot do, no matter what',
  '',
  '- Read SSH keys, AWS credentials, `.env` files, `.pem` files, or anything with "credentials" in the name.',
  ''
].join('\n');

test('parseProfileMd: reads title and italic summary', () => {
  const parsed = territory.parseProfileMd(HOUSECAT_PROFILE_MD);
  assert.equal(parsed.title, 'Curiosity Cat — Housecat profile (claude-code)');
  assert.match(parsed.summary, /Nothing leaves the yard/);
});

test('parseProfileMd: "can" bullets are verbatim substrings of the source, never reworded', () => {
  const parsed = territory.parseProfileMd(HOUSECAT_PROFILE_MD);
  const canTexts = parsed.can.map((b) => b.text);
  assert.ok(canTexts.some((t) => t === 'Read files inside this project.'));
  assert.ok(canTexts.some((t) => t === 'Write and edit files inside this project.'));
  assert.ok(canTexts.some((t) => t === 'Fetch pages only from:'));
  canTexts.forEach((t) => assert.ok(HOUSECAT_PROFILE_MD.indexOf(t) !== -1));
});

test('parseProfileMd: nested domain sub-bullets flatten in but stay flagged as sub-items', () => {
  const parsed = territory.parseProfileMd(HOUSECAT_PROFILE_MD);
  const domainItem = parsed.can.find((b) => b.text === 'docs.anthropic.com');
  assert.ok(domainItem);
  assert.equal(domainItem.sub, true);
  const topItem = parsed.can.find((b) => b.text === 'Fetch pages only from:');
  assert.equal(topItem.sub, false);
});

test('parseProfileMd: "cannot" and "safety net" sections are captured separately from "can"', () => {
  const parsed = territory.parseProfileMd(HOUSECAT_PROFILE_MD);
  assert.ok(parsed.cannot.some((b) => b.text.indexOf('sudo') !== -1));
  assert.ok(parsed.safetyNet.some((b) => b.text.indexOf('Sandbox: on') !== -1));
  assert.equal(parsed.cannot.some((b) => b.text.indexOf('Sandbox') !== -1), false);
});

test('parseProfileMd: a profile with no "ask first" section returns an empty askFirst list', () => {
  const parsed = territory.parseProfileMd(HOUSECAT_PROFILE_MD);
  assert.deepEqual(parsed.askFirst, []);
});

test('parseProfileMd: "ask first" bullets are captured under their own section only', () => {
  const parsed = territory.parseProfileMd(ALLEYCAT_PROFILE_MD_ASK_SECTION);
  const askTexts = parsed.askFirst.map((b) => b.text);
  assert.deepEqual(askTexts, ['`curl`', '`npm install`']);
  assert.equal(parsed.can.some((b) => b.text === '`curl`'), false);
});

test('buildWhatCanDoHtml: renders can/cannot/ask sections only when non-empty, backticks become <code>', () => {
  const html = territory.buildWhatCanDoHtml(territory.parseProfileMd(ALLEYCAT_PROFILE_MD_ASK_SECTION));
  assert.match(html, /Can do/);
  assert.match(html, /Has to ask first/);
  assert.match(html, /<code>curl<\/code>/);
});

test('buildWhatCanDoHtml: an empty parse falls back to an honest message, never a blank panel', () => {
  const html = territory.buildWhatCanDoHtml(territory.parseProfileMd(''));
  assert.match(html, /Could not read/);
});

test('buildWhatCanDoHtml: escapes HTML found in bullet text', () => {
  const parsed = { summary: '', can: [{ text: '<script>alert(1)</script>', sub: false }], cannot: [], askFirst: [] };
  const html = territory.buildWhatCanDoHtml(parsed);
  assert.equal(html.indexOf('<script>alert'), -1);
  assert.match(html, /&lt;script&gt;/);
});

test('TERRITORY_DATA: covers exactly the three adventure levels', () => {
  assert.deepEqual(Object.keys(territory.TERRITORY_DATA).sort(), ['alleycat', 'housecat', 'tiger']);
});

test('TERRITORY_DATA: fence widens monotonically from housecat to tiger', () => {
  const d = territory.TERRITORY_DATA;
  assert.ok(d.housecat.fenceWidthFrac < d.alleycat.fenceWidthFrac);
  assert.ok(d.alleycat.fenceWidthFrac < d.tiger.fenceWidthFrac);
});

test('TERRITORY_DATA: only tiger is wide-open on the web, matching LEVEL_POLICY.web_wide_open', () => {
  const d = territory.TERRITORY_DATA;
  assert.equal(d.housecat.wideOpenWeb, false);
  assert.equal(d.alleycat.wideOpenWeb, false);
  assert.equal(d.tiger.wideOpenWeb, true);
});

test('buildTerritorySvg: returns a self-contained, labelled <svg> per level', () => {
  ['housecat', 'alleycat', 'tiger'].forEach((level) => {
    const svg = territory.buildTerritorySvg(level);
    assert.match(svg, /^<svg /);
    assert.match(svg, /<\/svg>$/);
    assert.match(svg, new RegExp(territory.TERRITORY_DATA[level].fenceLabel));
  });
});

test('buildTerritorySvg: the always-off-limits band renders for every level', () => {
  ['housecat', 'alleycat', 'tiger'].forEach((level) => {
    const svg = territory.buildTerritorySvg(level);
    assert.match(svg, /OFF-LIMITS AT EVERY LEVEL/);
    assert.match(svg, /credentials/);
  });
});

test('buildTerritorySvg: housecat shows its allowed web trails as flags', () => {
  const svg = territory.buildTerritorySvg('housecat');
  assert.match(svg, /docs\.anthropic\.com/);
  assert.match(svg, /docs\.python\.org/);
});

test('buildTerritorySvg: tiger shows no allowlist, not a trail flag list', () => {
  const svg = territory.buildTerritorySvg('tiger');
  assert.match(svg, /no allowlist/);
  assert.equal(svg.indexOf('docs.anthropic.com'), -1);
});

test('buildTerritorySvg: alleycat renders an ask-first gate marker', () => {
  const svg = territory.buildTerritorySvg('alleycat');
  assert.match(svg, /asks first/);
});

test('buildTerritorySvg: an unknown level returns an empty string rather than throwing', () => {
  assert.equal(territory.buildTerritorySvg('nonexistent-level'), '');
});

test('buildExplainBlockHtml: always renders all three of what/from-what/since-when', () => {
  const html = territory.buildExplainBlockHtml({ what: 'housecat', fromWhat: 'the yard', sinceWhen: '2026-07-15' });
  assert.match(html, /What/);
  assert.match(html, /From what/);
  assert.match(html, /Since when/);
  assert.match(html, /housecat/);
  assert.match(html, /2026-07-15/);
});

test('buildExplainBlockHtml: a missing field renders an honest "unknown", never a blank claim', () => {
  const html = territory.buildExplainBlockHtml({ what: 'housecat' });
  assert.match(html, /unknown/);
});
