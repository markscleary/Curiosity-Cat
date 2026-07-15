// Curiosity Cat — the Feed (the Bell). Polls the Watcher listener
// (curiosity_cat/listen.py, spawned by the shell as its own process — see
// app/src-tauri/src/watcher.rs) directly over HTTP: one human sentence per
// event, Meow-spec three-sentence blocks laid out as distinct lines for
// denied events, tray icon state (app/src-tauri/src/tray.rs) driven off
// what just arrived via the tray-state.js state machine, and the approval
// gate's native dialog opened for any pending held event. Also polls the
// Guard Board's estate (curiosity_cat/discover.py, via CCAT.estate()) on a
// slower interval, since this hidden window is the app's one always-on
// background webview and so the natural place to keep the tray floored at
// hackles while any target is unguarded (Assignment Model (f)) — see
// tray-state.js's boardUnguarded floor.
(function () {
  'use strict';

  var WATCHER_ORIGIN = 'http://127.0.0.1:8377';
  var POLL_MS = 1500;
  var IDLE_RESET_MS = 8000;
  var BOARD_POLL_MS = 5000;

  var statusEl = document.getElementById('status');
  var listEl = document.getElementById('feed-list');

  var lastSeenMaxId = 0;
  var openApprovalIds = {};
  var idleTimer = null;
  // Carries over between polls so a burst of close calls keeps the tray
  // (and the feed's --pitch glow) hot across multiple 1.5s polls, not
  // just within a single one — see tray-state.js's DECAY.
  var trayHeat = 0;
  // The Guard Board's worst_state, refreshed every BOARD_POLL_MS. Starts
  // false (not yet known) rather than true, so a slow first estate() call
  // never flashes a false alarm before it resolves.
  var boardUnguarded = false;

  function setTray(state, pitch) {
    document.documentElement.style.setProperty('--pitch', pitch.toFixed(3));
    window.CCAT.setTrayState(state).catch(function () {});
  }

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

      var meowDiv = document.createElement('div');
      meowDiv.className = 'meow';
      // A denied block is three sentences (what tried / why no / what to
      // do) — one paragraph each, so it reads as a short explanation
      // rather than a single dense log line.
      (entry.meow_lines || [entry.meow]).forEach(function (sentence) {
        var p = document.createElement('p');
        p.textContent = sentence;
        meowDiv.appendChild(p);
      });

      var metaDiv = document.createElement('div');
      metaDiv.className = 'meta';
      metaDiv.textContent = '#' + entry.id + ' · ' + (entry.status || (entry.event || {}).verdict || '?') + ' · ' + entry.received_at;

      div.appendChild(meowDiv);
      div.appendChild(metaDiv);
      listEl.appendChild(div);
    });
  }

  function driveTrayState(newEntries) {
    if (!newEntries.length) return;

    var result = window.CCatTrayState.advance(trayHeat, newEntries, boardUnguarded);
    trayHeat = result.heat;
    setTray(result.state, result.pitch);

    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(function () {
      trayHeat = 0;
      var idle = window.CCatTrayState.advance(0, [], boardUnguarded);
      setTray(idle.state, idle.pitch);
    }, IDLE_RESET_MS);
  }

  function pollBoardState() {
    window.CCAT.estate()
      .then(function (inventory) {
        var nextUnguarded = inventory.worst_state !== 'guarded';
        if (nextUnguarded === boardUnguarded) return;
        boardUnguarded = nextUnguarded;
        // Re-apply the floor at the current heat immediately, rather than
        // waiting for the next Watcher event, so applying/undoing a profile
        // on the Guard Board is reflected on the tray right away.
        var result = window.CCatTrayState.advance(trayHeat, [], boardUnguarded);
        setTray(result.state, result.pitch);
      })
      .catch(function () {
        // Estate read failed (engine not up yet, etc.) — leave the last
        // known boardUnguarded alone rather than guessing either way.
      });
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
  pollBoardState();
  setInterval(pollBoardState, BOARD_POLL_MS);
})();
