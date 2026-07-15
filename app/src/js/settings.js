// Curiosity Cat — Settings window (APP-S1). Consent toggle for Danger Map
// reporting (default off, explicit — Network Layer Principle a), the
// optional remote-alarm webhook, the skin selector (wired to
// settings-store.js's unlock state, ported from site/js/skins.js's
// collectible layer), a read-only profile-home location, and an
// unapply-all/restore-backups safety control (the same action as the
// Guard Board's "Undo whole fleet", surfaced here as an emergency off
// switch). All state round-trips through get_settings/save_settings
// (settings.json in the app's own app_data_dir) rather than window-local
// storage, so every window agrees on it — same reasoning as
// get_last_profile_dir/set_last_profile_dir in commands.rs.
(function () {
  'use strict';

  var Store = window.CCatSettingsStore;

  var consentCheckbox = document.getElementById('consent-checkbox');
  var consentStatus = document.getElementById('consent-status');
  var webhookInput = document.getElementById('webhook-input');
  var saveWebhookBtn = document.getElementById('save-webhook-btn');
  var webhookStatus = document.getElementById('webhook-status');
  var skinGrid = document.getElementById('skin-grid');
  var skinStatus = document.getElementById('skin-status');
  var profileHomePath = document.getElementById('profile-home-path');
  var unapplyAllBtn = document.getElementById('unapply-all-btn');
  var safetyStatus = document.getElementById('safety-status');

  var confirmOverlay = document.getElementById('confirm-overlay');
  var confirmTitle = document.getElementById('confirm-title');
  var confirmBody = document.getElementById('confirm-body');
  var confirmList = document.getElementById('confirm-list');
  var confirmYesBtn = document.getElementById('confirm-yes-btn');
  var confirmNoBtn = document.getElementById('confirm-no-btn');

  // Starts at the library default (consent off) until the real persisted
  // state loads below, so a slow/failed load never leaves this window
  // reading (or capable of saving) any other value than the safe default.
  var current = Store.normalizeSettings({});

  function persist(patch, statusEl, okMessage) {
    var next = Store.normalizeSettings(Object.assign({}, current, patch));
    return window.CCAT.saveSettings(next).then(function () {
      current = next;
      if (statusEl) statusEl.textContent = okMessage;
    });
  }

  function renderSkinGrid() {
    skinGrid.innerHTML = '';
    var skinsData = (window.CC_SKINS && window.CC_SKINS.en) || {};
    Store.ALL_SKINS.forEach(function (name) {
      var data = skinsData[name];
      var unlocked = current.unlocked_skins.indexOf(name) !== -1;
      var li = document.createElement('li');
      li.className = (unlocked ? '' : 'locked') + (current.skin === name ? ' selected' : '');
      li.textContent = (data && data.name) || name;
      if (unlocked) {
        li.tabIndex = 0;
        li.setAttribute('role', 'button');
        li.addEventListener('click', function () { selectSkin(name); });
        li.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') {
            ev.preventDefault();
            selectSkin(name);
          }
        });
      } else {
        var lock = document.createElement('span');
        lock.textContent = ' 🔒';
        li.appendChild(lock);
      }
      skinGrid.appendChild(li);
    });
  }

  function selectSkin(name) {
    if (current.skin === name) return;
    persist({ skin: name }, skinStatus, 'Skin set to ' + name + '.')
      .then(renderSkinGrid)
      .catch(function (err) {
        skinStatus.textContent = 'Could not save: ' + err;
      });
  }

  consentCheckbox.addEventListener('change', function () {
    var next = consentCheckbox.checked === true;
    persist(
      { danger_map_consent: next },
      consentStatus,
      next ? 'Danger Map reporting enabled.' : 'Danger Map reporting disabled.'
    ).catch(function (err) {
      consentCheckbox.checked = current.danger_map_consent;
      consentStatus.textContent = 'Could not save: ' + err;
    });
  });

  saveWebhookBtn.addEventListener('click', function () {
    var value = webhookInput.value.trim();
    if (!Store.isValidWebhookUrl(value)) {
      webhookStatus.textContent = 'Not a valid http(s) URL — leave blank to disable the remote alarm.';
      return;
    }
    persist({ remote_alarm_webhook: value }, webhookStatus, 'Webhook saved.').catch(function (err) {
      webhookStatus.textContent = 'Could not save: ' + err;
    });
  });

  // Generic yes/no confirmation with an explicit list of what will
  // change — same pattern as board.js's Fleet actions (Assignment Model
  // (h): name exactly which targets change before anything is written).
  function showConfirm(title, body, items) {
    return new Promise(function (resolve) {
      confirmTitle.textContent = title;
      confirmBody.textContent = body;
      confirmList.innerHTML = '';
      items.forEach(function (item) {
        var li = document.createElement('li');
        li.textContent = item;
        confirmList.appendChild(li);
      });
      confirmOverlay.hidden = false;

      function cleanup(result) {
        confirmOverlay.hidden = true;
        confirmYesBtn.removeEventListener('click', onYes);
        confirmNoBtn.removeEventListener('click', onNo);
        resolve(result);
      }
      function onYes() { cleanup(true); }
      function onNo() { cleanup(false); }
      confirmYesBtn.addEventListener('click', onYes);
      confirmNoBtn.addEventListener('click', onNo);
    });
  }

  unapplyAllBtn.addEventListener('click', function () {
    window.CCAT.estate()
      .then(function (inventory) {
        var guarded = (inventory.targets || []).filter(function (t) {
          return t.protection && t.protection.status === 'guarded';
        });
        if (!guarded.length) {
          safetyStatus.textContent = 'Nothing is currently guarded — nothing to restore.';
          return;
        }
        var body = 'This restores each of the ' + guarded.length + ' guarded target(s) below to its ' +
          'pre-apply backup (or removes the applied settings.json if there was nothing there before).';
        return showConfirm('Unapply all / restore backups', body, guarded.map(function (t) { return t.label; }))
          .then(function (confirmed) {
            if (!confirmed) return;
            unapplyAllBtn.disabled = true;
            safetyStatus.textContent = 'Restoring ' + guarded.length + ' target(s)…';
            return window.CCAT.fleetUndo()
              .then(function (result) {
                safetyStatus.textContent = result.restored + ' of ' + result.outcomes.length +
                  ' target(s) restored, ' + result.failed + ' failed.';
              })
              .catch(function (err) {
                safetyStatus.textContent = 'Restore failed: ' + err;
              })
              .finally(function () {
                unapplyAllBtn.disabled = false;
              });
          });
      })
      .catch(function (err) {
        safetyStatus.textContent = 'Could not load the estate: ' + err;
      });
  });

  window.CCAT.getSettings()
    .then(function (raw) {
      current = Store.normalizeSettings(raw);
      consentCheckbox.checked = current.danger_map_consent;
      webhookInput.value = current.remote_alarm_webhook;
      renderSkinGrid();
    })
    .catch(function (err) {
      consentStatus.textContent = 'Could not load settings: ' + err;
      renderSkinGrid();
    });

  window.CCAT.getProfilesDir()
    .then(function (dir) {
      profileHomePath.textContent = dir;
    })
    .catch(function (err) {
      profileHomePath.textContent = 'Could not resolve: ' + err;
    });
})();
