// Curiosity Cat — the Guard Board. Lists every discovered target (the
// estate — see curiosity_cat/discover.py) with its honest per-target
// protection state (docs/app/APP_SPEC.md Assignment Model (e): what, from
// what, since when — never a bare "protected"), and hosts Fleet mode:
// "Protect whole fleet" applies one adventure level to every applicable
// target in one motion (core.apply_many(), via the sidecar's `fleet`
// method), "Undo whole fleet" restores every currently guarded target's
// pre-apply backup (core.unapply_many(), via `fleet_undo`). Both actions
// confirm first, listing exactly what will change, before touching
// anything real — Network Layer Principle e's "proposes, never silently
// rewrites" discipline, applied here to the fleet-wide action rather than
// a single Danger Map submission.
(function () {
  'use strict';

  var estateStatus = document.getElementById('estate-status');
  var targetListEl = document.getElementById('target-list');
  var levelPicker = document.getElementById('fleet-level');
  var protectBtn = document.getElementById('protect-fleet-btn');
  var undoBtn = document.getElementById('undo-fleet-btn');
  var fleetStatus = document.getElementById('fleet-status');
  var fleetResultsEl = document.getElementById('fleet-results');

  var confirmOverlay = document.getElementById('confirm-overlay');
  var confirmTitle = document.getElementById('confirm-title');
  var confirmBody = document.getElementById('confirm-body');
  var confirmList = document.getElementById('confirm-list');
  var confirmYesBtn = document.getElementById('confirm-yes-btn');
  var confirmNoBtn = document.getElementById('confirm-no-btn');

  var lastInventory = null;

  // Mirrors curiosity_cat.discover.format_protection() — the same
  // what/from-what/since-when sentence, rendered here instead of read back
  // from the engine, since the estate list is refreshed locally on every
  // poll rather than round-tripping a formatted string each time.
  function formatProtection(protection) {
    if (!protection || protection.status !== 'guarded') {
      return 'UNGUARDED — no profile applied, protects nothing';
    }
    var since = protection.applied_at ? ' since ' + protection.applied_at : ' (apply date unknown)';
    var proof = protection.proof_date ? ', last proved ' + protection.proof_date : ', never proved';
    return 'GUARDED — ' + (protection.level || 'unknown-level') + ' profile applied' + since + proof;
  }

  // The two discovered target kinds Fleet mode can actually act on — same
  // rule as cli.py's _fleet_applicable_targets() and serve.py's
  // _fleet_applicable_targets(): a Claude Code project directory, or the
  // literal "global" for the operator's own settings. Agent-workspace and
  // MCP-server targets are real, discovered targets too, but neither has a
  // settings.json of its own for apply() to write into.
  function fleetApplicableTargets(inventory) {
    var out = [];
    (inventory.targets || []).forEach(function (t) {
      if (t.kind === 'claude-code-project') {
        out.push({ label: t.label, arg: t.path });
      } else if (t.kind === 'claude-code-global') {
        out.push({ label: t.label, arg: 'global' });
      }
    });
    return out;
  }

  function renderTargetList(inventory) {
    targetListEl.innerHTML = '';
    var targets = inventory.targets || [];
    if (!targets.length) {
      var empty = document.createElement('li');
      empty.className = 'feed-empty';
      empty.textContent = 'No protectable surfaces found yet.';
      targetListEl.appendChild(empty);
      return;
    }
    targets.forEach(function (t) {
      var li = document.createElement('li');
      li.textContent = t.label + ' — ' + formatProtection(t.protection);
      targetListEl.appendChild(li);
    });
  }

  function loadEstate() {
    return window.CCAT.estate()
      .then(function (inventory) {
        lastInventory = inventory;
        estateStatus.textContent = (inventory.targets || []).length + ' target(s) found, discovered ' +
          inventory.discovered_at + '.';
        renderTargetList(inventory);
      })
      .catch(function (err) {
        estateStatus.textContent = 'Could not load the estate: ' + err;
      });
  }

  // Generic yes/no confirmation with an explicit list of what will
  // change — every Fleet action goes through this rather than acting
  // straight off a button click.
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

  function renderOutcomes(outcomes, describeOk) {
    fleetResultsEl.innerHTML = '';
    fleetResultsEl.hidden = false;
    outcomes.forEach(function (o) {
      var li = document.createElement('li');
      li.className = o.ok ? '' : 'held';
      li.textContent = o.target + ' — ' + (o.ok ? describeOk(o) : 'FAILED: ' + o.error);
      fleetResultsEl.appendChild(li);
    });
  }

  protectBtn.addEventListener('click', function () {
    if (!lastInventory) return;
    var level = levelPicker.value;
    var targets = fleetApplicableTargets(lastInventory);
    if (!targets.length) {
      fleetStatus.textContent = 'No applicable targets found — nothing to protect.';
      return;
    }

    var body = 'This applies the ' + level + ' profile to ' + targets.length + ' target(s) below. ' +
      "Each target's existing settings.json is backed up automatically first, and every change can be " +
      'undone afterwards with "Undo whole fleet".';
    showConfirm('Protect whole fleet — ' + level, body, targets.map(function (t) { return t.label; }))
      .then(function (confirmed) {
        if (!confirmed) return;
        protectBtn.disabled = true;
        undoBtn.disabled = true;
        fleetStatus.textContent = 'Applying ' + level + ' to ' + targets.length + ' target(s)…';
        return window.CCAT.fleet(level, true, targets.map(function (t) { return t.arg; }))
          .then(function (result) {
            renderOutcomes(result.outcomes, function (o) {
              return o.clean_bill && o.clean_bill.passed ? 'clean bill' : 'applied, but findings';
            });
            fleetStatus.textContent = 'Fleet Clean Bill — ' + result.agents_proven + ' of ' +
              result.outcomes.length + ' target(s) proven clean, ' + result.walls_proven +
              ' wall(s) held, ' + result.date + '.';
            return loadEstate();
          })
          .catch(function (err) {
            fleetStatus.textContent = 'Protect whole fleet failed: ' + err;
          })
          .finally(function () {
            protectBtn.disabled = false;
            undoBtn.disabled = false;
          });
      });
  });

  undoBtn.addEventListener('click', function () {
    if (!lastInventory) return;
    var guarded = (lastInventory.targets || []).filter(function (t) {
      return t.protection && t.protection.status === 'guarded';
    });
    if (!guarded.length) {
      fleetStatus.textContent = 'Nothing is currently guarded — nothing to undo.';
      return;
    }

    var body = 'This restores each of the ' + guarded.length + ' guarded target(s) below to its pre-apply ' +
      'backup (or removes the applied settings.json if there was nothing there before).';
    showConfirm('Undo whole fleet', body, guarded.map(function (t) { return t.label; }))
      .then(function (confirmed) {
        if (!confirmed) return;
        protectBtn.disabled = true;
        undoBtn.disabled = true;
        fleetStatus.textContent = 'Restoring ' + guarded.length + ' target(s)…';
        return window.CCAT.fleetUndo()
          .then(function (result) {
            renderOutcomes(result.outcomes, function (o) { return o.unapply_result.note; });
            fleetStatus.textContent = result.restored + ' of ' + result.outcomes.length +
              ' target(s) restored, ' + result.failed + ' failed.';
            return loadEstate();
          })
          .catch(function (err) {
            fleetStatus.textContent = 'Undo whole fleet failed: ' + err;
          })
          .finally(function () {
            protectBtn.disabled = false;
            undoBtn.disabled = false;
          });
      });
  });

  loadEstate();
})();
