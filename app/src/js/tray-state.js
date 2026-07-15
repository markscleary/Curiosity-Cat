// Curiosity Cat — tray icon state machine (APP-B1). Pure decision logic,
// no DOM and no Tauri: given a batch of new Watcher events, folds them
// onto a running "heat" score and picks the tray glyph
// (asleep/ears-up/hackles/mouse, tray.rs's STATE_* constants) plus a 0..1
// pitch the Feed can use to intensify its own colouring. Kept apart from
// feed.js so this can run under plain Node (tests/js/test_tray_state.js)
// without a browser or webview.
(function (global) {
  'use strict';

  var STATE_ASLEEP = 'asleep';
  var STATE_EARS_UP = 'ears-up';
  var STATE_HACKLES = 'hackles';
  var STATE_MOUSE = 'mouse';

  // Base urgency weight per state — how close to the fence line a single
  // event landed. A plain allowed pass-by is the mildest signal; a denied
  // or held brush with the fence is worse; a denied event that actually
  // carries a threat_class (queued to the Danger Map, curiosity_cat.listen
  // _should_queue) is the worst — a real tripwire, not just a wall doing
  // its job.
  var WEIGHT = {};
  WEIGHT[STATE_EARS_UP] = 1;
  WEIGHT[STATE_HACKLES] = 2;
  WEIGHT[STATE_MOUSE] = 3;

  // Heat decays by this factor before each new event is folded in, so a
  // burst of close calls keeps urgency high (pitch rises "as events
  // approach the fence line") while a quiet stretch lets it fall back on
  // its own between polls.
  var DECAY = 0.6;

  // Heat thresholds for the discrete tray glyph. A single mouse-grade
  // event always crosses THRESHOLD_MOUSE outright; hackles/ears-up need
  // to persist across the decay to stay lit, so one stray allowed event
  // right after a close call doesn't instantly calm the tray back down.
  var THRESHOLD_MOUSE = 2.5;
  var THRESHOLD_HACKLES = 1.5;
  var THRESHOLD_EARS_UP = 0.5;

  /**
   * The tray state a single event entry (the Watcher listener's /events
   * shape: {kind, status, event: {verdict, threat_class, ...}}) maps to
   * on its own, before heat/decay is folded in.
   */
  function stateForEntry(entry) {
    var event = entry.event || {};
    if (entry.kind === 'hold') {
      if (entry.status === 'pending') return STATE_HACKLES; // waiting on the fence right now
      if (entry.status === 'denied') return STATE_MOUSE; // the fence held even with a human asked
      return STATE_EARS_UP; // resolved allow — let through, back to routine
    }
    if (event.verdict === 'denied') {
      return event.threat_class ? STATE_MOUSE : STATE_HACKLES;
    }
    return STATE_EARS_UP;
  }

  function stateForHeat(heat) {
    if (heat >= THRESHOLD_MOUSE) return STATE_MOUSE;
    if (heat >= THRESHOLD_HACKLES) return STATE_HACKLES;
    if (heat >= THRESHOLD_EARS_UP) return STATE_EARS_UP;
    return STATE_ASLEEP;
  }

  /**
   * Fold a batch of new entries (oldest first) onto `heat` (the score
   * carried over from the previous call — 0 if none yet, or after an
   * idle reset to asleep), returning the next {state, heat, pitch}.
   * `pitch` is heat normalised to 0..1 against the mouse threshold, for
   * the Feed to use as a continuous intensity signal (e.g. a CSS custom
   * property) alongside the discrete glyph.
   */
  function advance(heat, entries) {
    var current = heat || 0;
    entries.forEach(function (entry) {
      current = current * DECAY + (WEIGHT[stateForEntry(entry)] || 0);
    });
    return {
      state: stateForHeat(current),
      heat: current,
      pitch: Math.max(0, Math.min(1, current / THRESHOLD_MOUSE)),
    };
  }

  var CCatTrayState = {
    STATE_ASLEEP: STATE_ASLEEP,
    STATE_EARS_UP: STATE_EARS_UP,
    STATE_HACKLES: STATE_HACKLES,
    STATE_MOUSE: STATE_MOUSE,
    stateForEntry: stateForEntry,
    advance: advance,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = CCatTrayState;
  } else {
    global.CCatTrayState = CCatTrayState;
  }
})(typeof window !== 'undefined' ? window : this);
