// Curiosity Cat — Settings persistence rules (APP-S1). Pure, DOM-free
// module — testable under plain Node (tests/js/test_settings_store.js,
// `node --test tests/js`) — same split as tray-state.js. Owns the shape of
// settings.json (get_settings/save_settings in commands.rs) and the
// unlock-state rules for the skin selector (ported from
// site/js/skin-unlocker.js's storage layer; the site's scroll/FAQ unlock
// triggers don't apply to the app shell and are not ported here).
(function (global) {
  'use strict';

  // Species skins ported from site/js/skins.js (app/src/js/skins.js carries
  // the full en-locale data; translations are a future i18n layer, not
  // wired into the app shell). "cat" ships unlocked in every profile.
  var ALL_SKINS = ['cat', 'puppy', 'rat', 'camel', 'panda', 'primate', 'cobra'];

  var DEFAULT_SETTINGS = {
    danger_map_consent: false,
    remote_alarm_webhook: '',
    skin: 'cat',
    unlocked_skins: ['cat']
  };

  function isValidSkinName(name) {
    return ALL_SKINS.indexOf(name) !== -1;
  }

  // "cat" is always present regardless of what's on disk — it's the one
  // skin v1 ships unlocked from a first launch, so a missing/corrupt/empty
  // persisted list can never leave the picker with nothing selectable.
  function normalizeUnlockedSkins(list) {
    var out = ['cat'];
    if (Array.isArray(list)) {
      list.forEach(function (name) {
        if (isValidSkinName(name) && out.indexOf(name) === -1) out.push(name);
      });
    }
    return out;
  }

  // Merges arbitrary/partial/corrupt persisted data onto the defaults.
  // `danger_map_consent` must be the literal boolean `true` to count as
  // consent — Network Layer Principle a ("consent as architecture") means a
  // stray truthy value read back from disk (a string, a stale "1") must
  // never be treated as an explicit opt-in. This is the one function the
  // Settings window and its tests both go through, so "default off" is
  // enforced in exactly one place.
  function normalizeSettings(raw) {
    var src = raw && typeof raw === 'object' ? raw : {};
    var unlockedSkins = normalizeUnlockedSkins(src.unlocked_skins);
    var skin = isValidSkinName(src.skin) && unlockedSkins.indexOf(src.skin) !== -1 ? src.skin : 'cat';
    return {
      danger_map_consent: src.danger_map_consent === true,
      remote_alarm_webhook: typeof src.remote_alarm_webhook === 'string' ? src.remote_alarm_webhook : '',
      skin: skin,
      unlocked_skins: unlockedSkins
    };
  }

  // Optional field: '' is a valid "not configured". Otherwise it must be a
  // syntactically valid http(s) URL — a remote alarm pointed at a typo'd or
  // non-http address is worse than not configured at all, since the
  // operator would believe an alarm is wired up when it cannot ever fire.
  function isValidWebhookUrl(value) {
    if (value === '') return true;
    if (typeof value !== 'string') return false;
    var parsed;
    try {
      parsed = new URL(value);
    } catch (e) {
      return false;
    }
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  }

  function unlockSkin(unlockedSkins, skinName) {
    var next = normalizeUnlockedSkins(unlockedSkins);
    if (isValidSkinName(skinName) && next.indexOf(skinName) === -1) {
      next.push(skinName);
    }
    return next;
  }

  var CCatSettingsStore = {
    ALL_SKINS: ALL_SKINS,
    DEFAULT_SETTINGS: DEFAULT_SETTINGS,
    isValidSkinName: isValidSkinName,
    normalizeSettings: normalizeSettings,
    isValidWebhookUrl: isValidWebhookUrl,
    unlockSkin: unlockSkin
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = CCatSettingsStore;
  } else {
    global.CCatSettingsStore = CCatSettingsStore;
  }
})(typeof window !== 'undefined' ? window : this);
