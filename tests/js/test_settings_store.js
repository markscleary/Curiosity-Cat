// Tests for Settings persistence rules (app/src/js/settings-store.js,
// APP-S1) — in particular that Danger Map reporting consent defaults off
// and stays off unless explicitly set to the literal boolean `true`
// (Network Layer Principle a: "consent as architecture").
// Run with: node --test tests/js
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const store = require('../../app/src/js/settings-store.js');

test('normalizeSettings: empty input defaults consent to false', () => {
  const settings = store.normalizeSettings({});
  assert.equal(settings.danger_map_consent, false);
});

test('normalizeSettings: undefined/null input defaults consent to false', () => {
  assert.equal(store.normalizeSettings(undefined).danger_map_consent, false);
  assert.equal(store.normalizeSettings(null).danger_map_consent, false);
});

test('normalizeSettings: a stray truthy non-boolean never counts as consent', () => {
  assert.equal(store.normalizeSettings({ danger_map_consent: 'true' }).danger_map_consent, false);
  assert.equal(store.normalizeSettings({ danger_map_consent: 1 }).danger_map_consent, false);
  assert.equal(store.normalizeSettings({ danger_map_consent: 'yes' }).danger_map_consent, false);
});

test('normalizeSettings: only the literal boolean true is treated as explicit consent', () => {
  assert.equal(store.normalizeSettings({ danger_map_consent: true }).danger_map_consent, true);
});

test('normalizeSettings: default settings carry no webhook and the base cat skin', () => {
  const settings = store.normalizeSettings({});
  assert.equal(settings.remote_alarm_webhook, '');
  assert.equal(settings.skin, 'cat');
  assert.deepEqual(settings.unlocked_skins, ['cat']);
});

test('normalizeSettings: a non-string webhook value is dropped back to the default', () => {
  assert.equal(store.normalizeSettings({ remote_alarm_webhook: 12345 }).remote_alarm_webhook, '');
});

test('normalizeSettings: "cat" is always present even if missing from a corrupt unlocked list', () => {
  assert.deepEqual(store.normalizeSettings({ unlocked_skins: [] }).unlocked_skins, ['cat']);
  assert.deepEqual(store.normalizeSettings({ unlocked_skins: null }).unlocked_skins, ['cat']);
});

test('normalizeSettings: unknown skin names in the unlocked list are dropped', () => {
  const settings = store.normalizeSettings({ unlocked_skins: ['cat', 'dragon', 'rat'] });
  assert.deepEqual(settings.unlocked_skins, ['cat', 'rat']);
});

test('normalizeSettings: a selected skin not in the unlocked list falls back to cat', () => {
  const settings = store.normalizeSettings({ skin: 'tiger', unlocked_skins: ['cat'] });
  assert.equal(settings.skin, 'cat');
});

test('normalizeSettings: a selected skin that is unlocked is respected', () => {
  const settings = store.normalizeSettings({ skin: 'rat', unlocked_skins: ['cat', 'rat'] });
  assert.equal(settings.skin, 'rat');
});

test('isValidWebhookUrl: empty string is valid (optional field, not configured)', () => {
  assert.equal(store.isValidWebhookUrl(''), true);
});

test('isValidWebhookUrl: accepts http and https URLs', () => {
  assert.equal(store.isValidWebhookUrl('https://example.com/hooks/curiosity-cat'), true);
  assert.equal(store.isValidWebhookUrl('http://127.0.0.1:9000/hook'), true);
});

test('isValidWebhookUrl: rejects non-URL strings and non-http(s) schemes', () => {
  assert.equal(store.isValidWebhookUrl('not a url'), false);
  assert.equal(store.isValidWebhookUrl('ftp://example.com/hook'), false);
  assert.equal(store.isValidWebhookUrl('javascript:alert(1)'), false);
});

test('isValidWebhookUrl: rejects non-string values', () => {
  assert.equal(store.isValidWebhookUrl(null), false);
  assert.equal(store.isValidWebhookUrl(42), false);
});

test('unlockSkin: adds a valid, not-yet-unlocked skin', () => {
  const next = store.unlockSkin(['cat'], 'rat');
  assert.deepEqual(next, ['cat', 'rat']);
});

test('unlockSkin: is a no-op for an already-unlocked skin', () => {
  const next = store.unlockSkin(['cat', 'rat'], 'rat');
  assert.deepEqual(next, ['cat', 'rat']);
});

test('unlockSkin: ignores an unknown skin name', () => {
  const next = store.unlockSkin(['cat'], 'dragon');
  assert.deepEqual(next, ['cat']);
});

test('isValidSkinName: recognises every ported species and rejects unknown names', () => {
  store.ALL_SKINS.forEach((name) => assert.equal(store.isValidSkinName(name), true));
  assert.equal(store.isValidSkinName('dragon'), false);
});
