// Tests for the tray icon state machine (app/src/js/tray-state.js,
// APP-B1) — state transitions from event fixtures shaped like the
// Watcher listener's /events entries (curiosity_cat/listen.py _EventLog).
// Run with: node --test tests/js
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const trayState = require('../../app/src/js/tray-state.js');

function eventEntry(id, verdict, threatClass) {
  return {
    id: id,
    kind: 'event',
    status: verdict,
    event: { tool: 'Bash', verdict: verdict, threat_class: threatClass || null },
  };
}

function holdEntry(id, status) {
  return { id: id, kind: 'hold', status: status, event: { tool: 'Bash', verdict: 'held' } };
}

test('stateForEntry: allowed event is ears-up', () => {
  assert.equal(trayState.stateForEntry(eventEntry(1, 'allowed')), trayState.STATE_EARS_UP);
});

test('stateForEntry: denied event without threat_class is hackles', () => {
  assert.equal(trayState.stateForEntry(eventEntry(1, 'denied')), trayState.STATE_HACKLES);
});

test('stateForEntry: denied event with threat_class is mouse', () => {
  assert.equal(
    trayState.stateForEntry(eventEntry(1, 'denied', 'credential-exposure')),
    trayState.STATE_MOUSE
  );
});

test('stateForEntry: pending hold is hackles (waiting on the fence right now)', () => {
  assert.equal(trayState.stateForEntry(holdEntry(1, 'pending')), trayState.STATE_HACKLES);
});

test('stateForEntry: hold resolved to denied is mouse', () => {
  assert.equal(trayState.stateForEntry(holdEntry(1, 'denied')), trayState.STATE_MOUSE);
});

test('stateForEntry: hold resolved to allowed is ears-up', () => {
  assert.equal(trayState.stateForEntry(holdEntry(1, 'allowed')), trayState.STATE_EARS_UP);
});

test('advance: empty batch leaves heat and state unchanged', () => {
  const result = trayState.advance(0, []);
  assert.equal(result.state, trayState.STATE_ASLEEP);
  assert.equal(result.heat, 0);
  assert.equal(result.pitch, 0);
});

test('advance: a single allowed event lands on ears-up, not higher', () => {
  const result = trayState.advance(0, [eventEntry(1, 'allowed')]);
  assert.equal(result.state, trayState.STATE_EARS_UP);
});

test('advance: a single denied event without threat_class lands on hackles', () => {
  const result = trayState.advance(0, [eventEntry(1, 'denied')]);
  assert.equal(result.state, trayState.STATE_HACKLES);
});

test('advance: a single denied event with threat_class always lands on mouse', () => {
  const result = trayState.advance(0, [eventEntry(1, 'denied', 'unsafe-url')]);
  assert.equal(result.state, trayState.STATE_MOUSE);
  assert.equal(result.pitch, 1);
});

test('advance: pitch rises monotonically as events approach the fence line', () => {
  const calm = trayState.advance(0, [eventEntry(1, 'allowed')]);
  const closeCall = trayState.advance(0, [eventEntry(1, 'denied')]);
  const tripwire = trayState.advance(0, [eventEntry(1, 'denied', 'data-exfiltration')]);
  assert.ok(calm.pitch < closeCall.pitch);
  assert.ok(closeCall.pitch < tripwire.pitch);
});

test('advance: a burst of hackles-grade events escalates to mouse even without a threat_class', () => {
  let heat = 0;
  let state = trayState.STATE_ASLEEP;
  [eventEntry(1, 'denied'), eventEntry(2, 'denied')].forEach((entry) => {
    const result = trayState.advance(heat, [entry]);
    heat = result.heat;
    state = result.state;
  });
  assert.equal(state, trayState.STATE_MOUSE);
});

test('advance: a lone allowed event after a mouse-grade spike does not reset heat to zero', () => {
  const spike = trayState.advance(0, [eventEntry(1, 'denied', 'unauthorized-tool-use')]);
  const after = trayState.advance(spike.heat, [eventEntry(2, 'allowed')]);
  assert.ok(after.heat > 0);
  assert.ok(after.heat < spike.heat);
});

test('advance: heat carried across polls keeps compounding for consecutive close calls', () => {
  const first = trayState.advance(0, [eventEntry(1, 'denied')]);
  const second = trayState.advance(first.heat, [eventEntry(2, 'denied')]);
  assert.ok(second.heat > first.heat);
});

test('advance: processes a mixed batch of fixtures in order, ending on the worst state', () => {
  const batch = [
    eventEntry(1, 'allowed'),
    holdEntry(2, 'pending'),
    eventEntry(3, 'denied', 'prompt-injection'),
  ];
  const result = trayState.advance(0, batch);
  assert.equal(result.state, trayState.STATE_MOUSE);
});
