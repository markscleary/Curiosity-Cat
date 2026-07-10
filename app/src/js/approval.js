// Curiosity Cat — the approval gate's dialog (APP_SPEC.md Watcher section:
// "app surfaces one-sentence Meow-spec prompt"). Opened by feed.js via
// open_approval_window for one pending held event; talks to the Watcher
// listener directly over HTTP, the same as the Feed does.
(function () {
  'use strict';

  var WATCHER_ORIGIN = 'http://127.0.0.1:8377';
  var POLL_MS = 1000;

  var params = new URLSearchParams(window.location.search);
  var entryId = Number(params.get('entryId'));
  var label = params.get('label');

  var promptEl = document.getElementById('prompt');
  var hintEl = document.getElementById('hint');
  var allowBtn = document.getElementById('allow-btn');
  var denyBtn = document.getElementById('deny-btn');

  var resolved = false;

  function closeSelf() {
    if (label) window.CCAT.closeWindow(label).catch(function () {});
  }

  function decide(decision) {
    if (resolved) return;
    resolved = true;
    allowBtn.disabled = true;
    denyBtn.disabled = true;
    fetch(WATCHER_ORIGIN + '/event/hold/' + entryId + '/decision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: decision })
    })
      .catch(function () {})
      .finally(closeSelf);
  }

  allowBtn.addEventListener('click', function () { decide('allow'); });
  denyBtn.addEventListener('click', function () { decide('deny'); });

  function poll() {
    if (resolved) return;
    fetch(WATCHER_ORIGIN + '/event/hold/pending')
      .then(function (response) { return response.json(); })
      .then(function (pending) {
        var match = pending.filter(function (e) { return e.id === entryId; })[0];
        if (!match) {
          // Already resolved elsewhere (timeout, or another window) — this
          // dialog has nothing left to do.
          resolved = true;
          promptEl.textContent = 'This one already got an answer.';
          hintEl.textContent = '';
          allowBtn.disabled = true;
          denyBtn.disabled = true;
          setTimeout(closeSelf, 1200);
          return;
        }
        promptEl.textContent = match.meow;
        hintEl.textContent = 'No response before the timeout counts as Deny.';
        allowBtn.disabled = false;
        denyBtn.disabled = false;
      })
      .catch(function (err) {
        promptEl.textContent = 'Could not reach the watcher: ' + err;
      });
  }

  poll();
  var timer = setInterval(function () {
    if (resolved) {
      clearInterval(timer);
      return;
    }
    poll();
  }, POLL_MS);
})();
