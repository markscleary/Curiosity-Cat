// Curiosity Cat — the Feed (the Bell). Polls the Watcher listener
// (curiosity_cat/listen.py, spawned by the shell as its own process — see
// app/src-tauri/src/watcher.rs) directly over HTTP: one human sentence per
// event, Meow-spec three-sentence blocks for denied events, tray icon
// state driven off what just arrived, and the approval gate's native
// dialog opened for any pending held event.
(function () {
  'use strict';

  var WATCHER_ORIGIN = 'http://127.0.0.1:8377';
  var POLL_MS = 1500;
  var IDLE_RESET_MS = 8000;

  var statusEl = document.getElementById('status');
  var listEl = document.getElementById('feed-list');

  var lastSeenMaxId = 0;
  var openApprovalIds = {};
  var idleTimer = null;

  function verdictClass(entry) {
    if (entry.kind === 'hold') {
      return entry.status === 'pending' ? 'verdict-held' : (entry.status === 'denied' ? 'verdict-denied' : 'verdict-allowed');
    }
    var v = (entry.event || {}).verdict;
    if (v === 'denied') return 'verdict-denied';
    if (v === 'held') return 'verdict-held';
    return 'verdict-allowed';
  }

  function render(entries) {
    listEl.innerHTML = '';
    if (!entries.length) {
      var empty = document.createElement('p');
      empty.className = 'feed-empty';
      empty.textContent = 'No events yet. Nothing has tried the fence.';
      listEl.appendChild(empty);
      return;
    }
    entries.slice().reverse().forEach(function (entry) {
      var div = document.createElement('div');
      div.className = 'feed-item ' + verdictClass(entry);
      var meta = '#' + entry.id + ' · ' + (entry.status || (entry.event || {}).verdict || '?') + ' · ' + entry.received_at;
      div.innerHTML = '<div class="meow">' + escapeHtml(entry.meow) + '</div>' +
        '<div class="meta">' + escapeHtml(meta) + '</div>';
      listEl.appendChild(div);
    });
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
  }

  function driveTrayState(newEntries) {
    if (!newEntries.length) return;

    var state = null; // priority: mouse > hackles > ears-up
    newEntries.forEach(function (entry) {
      var event = entry.event || {};
      var candidate = null;
      if (entry.kind === 'hold' && entry.status === 'pending') {
        candidate = 'ears-up';
      } else if (event.verdict === 'denied') {
        candidate = event.threat_class ? 'mouse' : 'hackles';
      } else {
        candidate = 'ears-up';
      }
      var rank = { 'mouse': 3, 'hackles': 2, 'ears-up': 1 };
      if (!state || rank[candidate] > rank[state]) state = candidate;
    });

    if (!state) return;
    window.CCAT.setTrayState(state).catch(function () {});

    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(function () {
      window.CCAT.setTrayState('asleep').catch(function () {});
    }, IDLE_RESET_MS);
  }

  function openApprovalDialogsFor(newEntries) {
    newEntries.forEach(function (entry) {
      if (entry.kind !== 'hold' || entry.status !== 'pending') return;
      if (openApprovalIds[entry.id]) return;
      openApprovalIds[entry.id] = true;
      window.CCAT.openApprovalWindow(entry.id).catch(function () {});
    });
  }

  function poll() {
    window.CCAT.getLastProfileDir()
      .then(function (profileDir) {
        if (!profileDir) {
          statusEl.textContent = 'No compiled profile yet — open the Slider and compile one first.';
          return;
        }
        return fetch(WATCHER_ORIGIN + '/events')
          .then(function (response) {
            if (!response.ok) throw new Error('listener returned ' + response.status);
            return response.json();
          })
          .then(function (entries) {
            statusEl.textContent = entries.length + ' event(s) since the watcher started.';
            render(entries);

            var maxId = entries.length ? Math.max.apply(Math, entries.map(function (e) { return e.id; })) : 0;
            if (maxId < lastSeenMaxId) {
              // The watcher process restarted (e.g. after a recompile) —
              // its event ids started over from 1, so the old high-water
              // mark is stale and would silently swallow every "new"
              // event until the fresh log grew past it.
              lastSeenMaxId = 0;
              openApprovalIds = {};
            }
            var newEntries = entries.filter(function (e) { return e.id > lastSeenMaxId; });
            if (entries.length) lastSeenMaxId = maxId;
            driveTrayState(newEntries);
            openApprovalDialogsFor(newEntries);
          });
      })
      .catch(function (err) {
        statusEl.textContent = 'Feed read failed (is the watcher running?): ' + err;
      });
  }

  poll();
  setInterval(poll, POLL_MS);
})();
