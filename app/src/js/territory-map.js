// Curiosity Cat — the explanation layer (APP-T1). Pure, DOM-free core —
// testable under plain Node (tests/js/test_territory_map.js, `node --test
// tests/js`), same split as tray-state.js/settings-store.js. Three things
// live here:
//
//   1. TERRITORY_DATA — a small, deliberate mirror of curiosity_cat/core.py's
//      LEVEL_POLICY *abstract* knobs (read_scope, write_scope,
//      web_wide_open, web_allowed_domains, bash_ask) — only the fields
//      build_profile_md() itself renders into PROFILE.md. The three levels
//      are fixed product decisions, not user-configurable, so this mirror
//      is a deliberate duplication for illustration purposes (same
//      justification as WATCHER_HOST/WATCHER_PORT's mirror in core.py: no
//      import-cycle-free way to share it with a Python module, so it must
//      be kept in sync by hand whenever LEVEL_POLICY changes). It never
//      substitutes for PROFILE.md as the source of truth for a protection
//      claim — see parseProfileMd() below for that.
//   2. buildTerritorySvg(level) — an inline, original SVG (no external
//      assets) drawing the fence line: what's inside (reads/writes/allowed
//      web trails), what's outside, and the always-off-limits band that
//      holds at every level regardless of slider position.
//   3. parseProfileMd(text) / buildWhatCanDoHtml(parsed) — turn the
//      engine's own already-compiled PROFILE.md text (build_profile_md() in
//      curiosity_cat/core.py) into a structured "What can this cat do?"
//      panel, so that panel's wording can never drift from the compiled
//      product: it is the same text, restructured, never reworded.
//   4. buildExplainBlockHtml() — the what/from-what/since-when triplet
//      docs/app/APP_SPEC.md's Assignment Model (e) requires on every
//      surface that states a protection claim.
(function (global) {
  'use strict';

  var TERRITORY_DATA = {
    housecat: {
      label: 'Housecat',
      color: '#22c55e',
      fenceLabel: 'the yard',
      fenceWidthFrac: 0.22,
      insideCaptions: ['reads & writes: this project only'],
      wideOpenWeb: false,
      trails: ['docs.anthropic.com', 'docs.python.org'],
      askFirst: []
    },
    alleycat: {
      label: 'Alley Cat',
      color: '#d97706',
      fenceLabel: 'the neighborhood',
      fenceWidthFrac: 0.52,
      insideCaptions: ['reads: anywhere', 'writes: this project only'],
      wideOpenWeb: false,
      trails: ['docs.anthropic.com', 'docs.python.org', 'github.com', 'pypi.org', 'npmjs.com', 'stackoverflow.com'],
      askFirst: ['curl', 'wget', 'npm install', 'pip install', 'pip3 install', 'brew install', 'yarn add']
    },
    tiger: {
      label: 'Tiger',
      color: '#b45309',
      fenceWidthFrac: 0.9,
      fenceLabel: 'the wide range',
      insideCaptions: ['reads & writes: anywhere on this machine'],
      wideOpenWeb: true,
      trails: [],
      askFirst: []
    }
  };

  // Constant across every level — mirrors PROFILE.md's unconditional
  // "cannot do, no matter what" bullets in build_profile_md().
  var ALWAYS_OFFLIMITS_LABEL = 'OFF-LIMITS AT EVERY LEVEL — credentials, SSH keys, .env, sudo, rm -rf';

  function escapeXml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function truncateList(list, max) {
    if (list.length <= max) return list.join(', ');
    return list.slice(0, max).join(', ') + ', +' + (list.length - max) + ' more';
  }

  // A small original vector cat glyph — circle head, two triangle ears, a
  // curled tail stroke. Deliberately not the 🐱 emoji (font-support
  // portability, same reasoning as card.py's share-card glyph) and not any
  // copyrighted character art — plain geometric shapes only.
  function catGlyphSvg(cx, cy, color) {
    var r = 7;
    return (
      '<g>' +
      '<path d="M ' + (cx - r * 0.9) + ' ' + (cy - r * 0.6) + ' L ' + (cx - r * 0.3) + ' ' + (cy - r * 1.5) +
        ' L ' + (cx - r * 0.1) + ' ' + (cy - r * 0.7) + ' Z" fill="' + color + '"/>' +
      '<path d="M ' + (cx + r * 0.9) + ' ' + (cy - r * 0.6) + ' L ' + (cx + r * 0.3) + ' ' + (cy - r * 1.5) +
        ' L ' + (cx + r * 0.1) + ' ' + (cy - r * 0.7) + ' Z" fill="' + color + '"/>' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="' + color + '"/>' +
      '<path d="M ' + (cx + r) + ' ' + cy + ' Q ' + (cx + r * 2.4) + ' ' + (cy - r * 0.6) + ' ' + (cx + r * 2.1) + ' ' + (cy - r * 1.8) +
        '" stroke="' + color + '" stroke-width="1.6" fill="none" stroke-linecap="round"/>' +
      '</g>'
    );
  }

  // Builds the territory diagram as a self-contained inline <svg> string —
  // original art, no external/copyrighted assets. Fence line visible as a
  // dashed rounded rect sized proportional to that level's actual reach
  // (TERRITORY_DATA.fenceWidthFrac); allowlisted web domains render as
  // flags on marked trails outside the fence; a wide-open level (tiger)
  // renders an open edge instead of a fence line on that side.
  function buildTerritorySvg(level) {
    var data = TERRITORY_DATA[level];
    if (!data) return '';

    var W = 520, H = 220, PAD = 14;
    var bandH = 26;
    var bandY = PAD;
    var mainY = bandY + bandH + 10;
    var mainH = H - mainY - PAD;
    var mainW = W - PAD * 2;
    var fenceX = PAD;
    var fenceY = mainY;
    var fenceH = mainH;
    var fenceW = Math.round(mainW * data.fenceWidthFrac);
    var color = data.color;
    var hatchId = 'ccat-hatch-' + level;

    var parts = [];
    parts.push('<svg viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg" role="img" ' +
      'aria-label="Territory diagram for the ' + escapeXml(data.label) + ' level: what is inside the fence, ' +
      'what is outside.">');
    parts.push(
      '<defs><pattern id="' + hatchId + '" width="8" height="8" patternTransform="rotate(45)" ' +
      'patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#fee2e2"/>' +
      '<line x1="0" y1="0" x2="0" y2="8" stroke="#dc2626" stroke-width="2"/></pattern></defs>'
    );
    parts.push('<rect x="0" y="0" width="' + W + '" height="' + H + '" rx="10" fill="#fffaf3"/>');

    // Always-off-limits band — constant across every level.
    parts.push(
      '<rect x="' + PAD + '" y="' + bandY + '" width="' + mainW + '" height="' + bandH + '" rx="4" ' +
      'fill="url(#' + hatchId + ')" stroke="#dc2626" stroke-width="1"/>'
    );
    parts.push(
      '<text x="' + (PAD + mainW / 2) + '" y="' + (bandY + bandH / 2 + 3.5) + '" text-anchor="middle" ' +
      'font-size="9" font-weight="700" fill="#991b1b">' + escapeXml(ALWAYS_OFFLIMITS_LABEL) + '</text>'
    );

    // "Everywhere else" — the rest of the machine and the open web.
    parts.push(
      '<rect x="' + PAD + '" y="' + mainY + '" width="' + mainW + '" height="' + mainH + '" rx="8" ' +
      'fill="#f3f1ea" stroke="#ecdfcb" stroke-width="1"/>'
    );

    // The fence itself.
    var openRight = data.wideOpenWeb && fenceW > mainW - 20;
    var fenceDash = openRight ? '' : ' stroke-dasharray="7 5"';
    parts.push(
      '<rect x="' + fenceX + '" y="' + fenceY + '" width="' + fenceW + '" height="' + fenceH + '" rx="10" ' +
      'fill="' + color + '22" stroke="' + color + '" stroke-width="2.5"' + fenceDash + '/>'
    );
    parts.push(
      '<text x="' + (fenceX + 10) + '" y="' + (fenceY + 19) + '" font-size="12.5" font-weight="700" ' +
      'fill="' + color + '">' + escapeXml(data.fenceLabel) + '</text>'
    );

    var catCx = fenceX + 20, catCy = fenceY + fenceH - 22;
    parts.push(catGlyphSvg(catCx, catCy, color));

    var capY = fenceY + 38;
    data.insideCaptions.forEach(function (cap) {
      parts.push(
        '<text x="' + (fenceX + 10) + '" y="' + capY + '" font-size="9.5" fill="#1f2937">' +
        escapeXml(cap) + '</text>'
      );
      capY += 13;
    });

    if (data.askFirst.length) {
      var gateX = fenceX + fenceW - 4, gateY = fenceY + fenceH - 16;
      parts.push('<circle cx="' + gateX + '" cy="' + gateY + '" r="8" fill="#fef3c7" stroke="#92400e" stroke-width="1.5"/>');
      parts.push('<text x="' + gateX + '" y="' + (gateY + 3.2) + '" text-anchor="middle" font-size="10" fill="#92400e">?</text>');
      parts.push(
        '<text x="' + (fenceX + 10) + '" y="' + (fenceY + fenceH - 6) + '" font-size="8.5" fill="#92400e">' +
        'asks first: ' + escapeXml(truncateList(data.askFirst, 3)) + '</text>'
      );
    }

    if (data.wideOpenWeb) {
      var arrowX = fenceX + fenceW;
      parts.push(
        '<path d="M ' + arrowX + ' ' + (fenceY + fenceH / 2) + ' L ' + (arrowX + 14) + ' ' + (fenceY + fenceH / 2) +
        ' M ' + (arrowX + 8) + ' ' + (fenceY + fenceH / 2 - 5) + ' L ' + (arrowX + 14) + ' ' + (fenceY + fenceH / 2) +
        ' L ' + (arrowX + 8) + ' ' + (fenceY + fenceH / 2 + 5) +
        '" stroke="' + color + '" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
      );
      parts.push(
        '<text x="' + (fenceX + fenceW - 8) + '" y="' + (fenceY + fenceH + 12) + '" text-anchor="end" ' +
        'font-size="8.5" fill="' + color + '">no wall here — any web page, no allowlist</text>'
      );
    } else if (data.trails.length) {
      var maxFlags = 4;
      var flagX = fenceX + fenceW + 26;
      var flagStartY = fenceY + 22;
      var flagGap = (fenceH - 30) / Math.min(data.trails.length, maxFlags);
      data.trails.slice(0, maxFlags).forEach(function (domain, i) {
        var fy = flagStartY + i * flagGap;
        parts.push(
          '<line x1="' + (fenceX + fenceW) + '" y1="' + fy + '" x2="' + (flagX - 6) + '" y2="' + fy +
          '" stroke="' + color + '" stroke-width="1.2" stroke-dasharray="3 3"/>'
        );
        parts.push('<path d="M ' + flagX + ' ' + (fy - 5) + ' L ' + flagX + ' ' + (fy + 5) +
          ' M ' + flagX + ' ' + (fy - 5) + ' L ' + (flagX + 9) + ' ' + (fy - 2) + ' L ' + flagX + ' ' + fy +
          '" stroke="' + color + '" stroke-width="1.4" fill="' + color + '" stroke-linejoin="round"/>');
        parts.push(
          '<text x="' + (flagX + 13) + '" y="' + (fy + 3) + '" font-size="8.5" fill="#1f2937">' +
          escapeXml(domain) + '</text>'
        );
      });
      if (data.trails.length > maxFlags) {
        var moreY = flagStartY + maxFlags * flagGap;
        parts.push(
          '<text x="' + (flagX + 13) + '" y="' + (Math.min(moreY, fenceY + fenceH - 4)) + '" font-size="8" ' +
          'fill="#6b7280">+' + (data.trails.length - maxFlags) + ' more trail(s)</text>'
        );
      }
      parts.push(
        '<text x="' + (W - PAD - 6) + '" y="' + (fenceY + fenceH + 12) + '" text-anchor="end" font-size="8.5" ' +
        'fill="#6b7280">everywhere else — denied</text>'
      );
    } else {
      parts.push(
        '<text x="' + (W - PAD - 6) + '" y="' + (fenceY + fenceH + 12) + '" text-anchor="end" font-size="8.5" ' +
        'fill="#6b7280">everywhere else — denied</text>'
      );
    }

    parts.push('</svg>');
    return parts.join('');
  }

  // --- PROFILE.md -> structured panel -----------------------------------
  //
  // Parses the exact text build_profile_md() (curiosity_cat/core.py)
  // writes for a compiled profile. Never invents or rewords a line — every
  // bullet in the returned lists is a substring of the source text, so the
  // "What can this cat do?" panel can never say something the compiled
  // profile doesn't.
  var SECTION_HEADINGS = {
    '## What this cat can do': 'can',
    '## What this cat cannot do, no matter what': 'cannot',
    '## What this cat has to ask about first': 'askFirst',
    '## The safety net underneath': 'safetyNet'
  };

  function parseProfileMd(text) {
    var result = { title: '', summary: '', can: [], cannot: [], askFirst: [], safetyNet: [] };
    var lines = String(text || '').split('\n');
    var section = null;

    lines.forEach(function (raw) {
      var trimmed = raw.trim();
      if (!trimmed) return;

      if (SECTION_HEADINGS.hasOwnProperty(trimmed)) {
        section = SECTION_HEADINGS[trimmed];
        return;
      }
      if (trimmed.indexOf('## ') === 0) {
        section = null;
        return;
      }
      if (trimmed.indexOf('# ') === 0 && !result.title) {
        result.title = trimmed.replace(/^#\s*/, '');
        return;
      }
      if (!result.summary && trimmed.charAt(0) === '*' && trimmed.charAt(trimmed.length - 1) === '*') {
        result.summary = trimmed.replace(/^\*+|\*+$/g, '');
        return;
      }

      var bulletMatch = raw.match(/^(\s*)-\s?(.*)$/);
      if (bulletMatch && section && result[section]) {
        result[section].push({ text: bulletMatch[2], sub: bulletMatch[1].length >= 2 });
      }
    });

    return result;
  }

  function mdInlineToHtml(text) {
    return escapeXml(text).replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  function buildBulletListHtml(items, marker, markerClass) {
    if (!items.length) return '';
    return '<ul class="whatcan-list">' + items.map(function (item) {
      var cls = 'whatcan-item ' + markerClass + (item.sub ? ' whatcan-item-sub' : '');
      return '<li class="' + cls + '"><span class="whatcan-marker" aria-hidden="true">' + marker + '</span>' +
        '<span>' + mdInlineToHtml(item.text) + '</span></li>';
    }).join('') + '</ul>';
  }

  // Renders the parsed PROFILE.md into the "What can this cat do?" panel:
  // green-check "can", red-cross "cannot, ever", amber-"?" "asks first".
  // Falls back to an honest empty state rather than a blank panel if
  // parsing found nothing (e.g. an unexpected/older PROFILE.md shape).
  function buildWhatCanDoHtml(parsed) {
    var out = [];
    if (parsed.summary) {
      out.push('<p class="whatcan-summary">' + mdInlineToHtml(parsed.summary) + '</p>');
    }
    if (parsed.can.length) {
      out.push('<h3 class="whatcan-heading">Can do</h3>');
      out.push(buildBulletListHtml(parsed.can, '✓', 'whatcan-can'));
    }
    if (parsed.cannot.length) {
      out.push('<h3 class="whatcan-heading">Cannot do, no matter what</h3>');
      out.push(buildBulletListHtml(parsed.cannot, '✕', 'whatcan-cannot'));
    }
    if (parsed.askFirst.length) {
      out.push('<h3 class="whatcan-heading">Has to ask first</h3>');
      out.push(buildBulletListHtml(parsed.askFirst, '?', 'whatcan-ask'));
    }
    if (!out.length) {
      out.push('<p class="whatcan-summary">Could not read this profile’s PROFILE.md.</p>');
    }
    return out.join('');
  }

  // The what/from-what/since-when triplet docs/app/APP_SPEC.md's Assignment
  // Model (e) requires on every surface stating a protection claim. Every
  // field is required text, not optional — an honest "not yet applied" /
  // "not yet proved" string is a valid value, a missing one is not.
  function buildExplainBlockHtml(opts) {
    opts = opts || {};
    var rows = [
      ['What', opts.what],
      ['From what', opts.fromWhat],
      ['Since when', opts.sinceWhen]
    ];
    return '<dl class="explain-block">' + rows.map(function (row) {
      return '<div class="explain-row"><dt>' + escapeXml(row[0]) + '</dt><dd>' +
        mdInlineToHtml(row[1] || 'unknown') + '</dd></div>';
    }).join('') + '</dl>';
  }

  var CCatTerritory = {
    TERRITORY_DATA: TERRITORY_DATA,
    ALWAYS_OFFLIMITS_LABEL: ALWAYS_OFFLIMITS_LABEL,
    buildTerritorySvg: buildTerritorySvg,
    parseProfileMd: parseProfileMd,
    buildWhatCanDoHtml: buildWhatCanDoHtml,
    buildExplainBlockHtml: buildExplainBlockHtml
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = CCatTerritory;
  } else {
    global.CCatTerritory = CCatTerritory;

    // Thin DOM-touching wrappers — only defined in a browser context.
    global.CCAT_renderTerritoryDiagram = function (container, level) {
      if (!container) return;
      container.innerHTML = buildTerritorySvg(level);
    };
    global.CCAT_renderWhatCanDo = function (container, profileMdText) {
      if (!container) return;
      container.innerHTML = buildWhatCanDoHtml(parseProfileMd(profileMdText));
    };
    global.CCAT_renderExplainBlock = function (container, opts) {
      if (!container) return;
      container.innerHTML = buildExplainBlockHtml(opts);
    };
  }
})(typeof window !== 'undefined' ? window : this);
