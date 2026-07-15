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
  var worstStateBanner = document.getElementById('worst-state-banner');
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

  var detailOverlay = document.getElementById('detail-overlay');
  var detailTitle = document.getElementById('detail-title');
  var detailStatus = document.getElementById('detail-status');
  var detailFromWhat = document.getElementById('detail-from-what');
  var detailCloseBtn = document.getElementById('detail-close-btn');

  var lastInventory = null;

  // discover.Target.kind -> a short label for the row's kind badge.
  var KIND_LABELS = {
    'claude-code-project': 'Project',
    'claude-code-global': 'Global',
    'agent-process': 'Agent',
    'mcp-server': 'MCP Server',
  };

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

  // Assignment Model (e): what/from-what/since-when must always be
  // answerable, in plain colour-coded state — three buckets, never a bare
  // "protected". A guarded-but-never-proved target reads as a distinct
  // amber state rather than green, since Assignment Model (d)/(e) treat an
  // un-proved apply as an honest but incomplete claim.
  function stateClass(protection) {
    if (!protection || protection.status !== 'guarded') return 'state-unguarded';
    return protection.proof_date ? 'state-guarded' : 'state-guarded-unproven';
  }

  function statePillText(protection) {
    return protection && protection.status === 'guarded' ? 'GUARDED' : 'UNGUARDED';
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

  // Assignment Model (a)/(e): what a drill-down honestly says a target is
  // protected from. For an unguarded target there is nothing to describe —
  // just the same honest sentence the row itself shows. For a guarded one,
  // read back the compiled profile's own PROFILE.md (build_profile_md() in
  // curiosity_cat/core.py) rather than re-deriving a wall list here: that
  // file is written at compile time from the same policy the applied
  // settings.json was compiled from, in C-Cat's own voice, so this reuses
  // the engine's honesty layer instead of risking it drifting out of sync.
  function showTargetDetail(target) {
    var protection = target.protection;
    detailTitle.textContent = target.label;
    detailStatus.textContent = formatProtection(protection);
    detailFromWhat.innerHTML = '';

    if (!protection || protection.status !== 'guarded' || !protection.profile_dir) {
      detailOverlay.hidden = false;
      return;
    }

    var pre = document.createElement('pre');
    pre.className = 'profile-md';
    pre.textContent = 'Loading what this profile protects against…';
    detailFromWhat.appendChild(pre);
    detailOverlay.hidden = false;

    var profileMdPath = protection.profile_dir.replace(/\/+$/, '') + '/PROFILE.md';
    window.CCAT.readTextFile(profileMdPath)
      .then(function (text) {
        pre.textContent = text;
      })
      .catch(function (err) {
        pre.textContent = 'Could not read this profile\'s PROFILE.md: ' + err;
      });
  }

  function hideTargetDetail() {
    detailOverlay.hidden = true;
  }

  detailCloseBtn.addEventListener('click', hideTargetDetail);
  detailOverlay.addEventListener('click', function (ev) {
    if (ev.target === detailOverlay) hideTargetDetail();
  });

  function renderTargetList(inventory) {
    targetListEl.innerHTML = '';
    var targets = inventory.targets || [];
    if (!targets.length) {
      var empty = document.createElement('li');
      empty.className = 'feed-empty';
      empty.textContent = 'No protectable surfaces found yet — nothing here to guard, honestly.';
      targetListEl.appendChild(empty);
      return;
    }
    targets.forEach(function (t) {
      var li = document.createElement('li');
      li.className = 'target-row';
      li.tabIndex = 0;
      li.setAttribute('role', 'button');
      li.setAttribute('aria-label', t.label + ' — ' + formatProtection(t.protection));

      var kind = document.createElement('span');
      kind.className = 'target-kind';
      kind.textContent = KIND_LABELS[t.kind] || t.kind;

      var name = document.createElement('span');
      name.className = 'target-name';
      name.textContent = t.label;

      var pill = document.createElement('span');
      pill.className = 'target-pill ' + stateClass(t.protection);
      pill.textContent = statePillText(t.protection);

      var level = document.createElement('span');
      level.className = 'target-level';
      level.textContent = (t.protection && t.protection.level) || '—';

      var proof = document.createElement('span');
      proof.className = 'target-proof';
      proof.textContent = t.protection && t.protection.proof_date
        ? 'proved ' + t.protection.proof_date
        : 'never proved';

      li.appendChild(kind);
      li.appendChild(name);
      li.appendChild(pill);
      li.appendChild(level);
      li.appendChild(proof);

      li.addEventListener('click', function () { showTargetDetail(t); });
      li.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          showTargetDetail(t);
        }
      });

      targetListEl.appendChild(li);
    });
  }

  function renderWorstStateBanner(inventory) {
    var worst = inventory.worst_state;
    worstStateBanner.hidden = false;
    if (worst === 'guarded') {
      worstStateBanner.textContent = 'Worst state on the board: GUARDED — every discovered target has an applied profile.';
      worstStateBanner.className = 'worst-state-banner state-guarded';
    } else {
      worstStateBanner.textContent = 'Worst state on the board: UNGUARDED — at least one discovered target has no applied profile.';
      worstStateBanner.className = 'worst-state-banner state-unguarded';
    }
  }

  function loadEstate() {
    return window.CCAT.estate()
      .then(function (inventory) {
        lastInventory = inventory;
        var targets = inventory.targets || [];
        estateStatus.textContent = targets.length
          ? targets.length + ' target(s) found, discovered ' + inventory.discovered_at + '.'
          : 'Discovery ran on ' + inventory.discovered_at + ' and found nothing yet to protect.';
        renderTargetList(inventory);
        if (targets.length) {
          renderWorstStateBanner(inventory);
        } else {
          worstStateBanner.hidden = true;
        }
      })
      .catch(function (err) {
        worstStateBanner.hidden = true;
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
