// Curiosity Cat — This Week's Purr window. One-shot fetch (not a poll
// loop like feed.js): the Purr is a digest, not a live stream, and
// re-generating it is cheap enough to just do on window open.
(function () {
  'use strict';

  var statusEl = document.getElementById('status');
  var textEl = document.getElementById('purr-text');

  window.CCAT.getLastProfileDir()
    .then(function (profileDir) {
      if (!profileDir) {
        statusEl.textContent = 'No compiled profile yet — open the Slider and compile one first.';
        return;
      }
      return window.CCAT.purr(profileDir).then(function (result) {
        statusEl.textContent = 'Last 7 days.';
        textEl.textContent = result.text;
      });
    })
    .catch(function (err) {
      statusEl.textContent = 'Purr failed: ' + err;
    });
})();
