// Curiosity Cat — Adventure Slider

(function () {
  'use strict';

  var LS_SKIN = 'curiosity-cat-current-skin';
  var LS_LEVEL = 'curiosity-cat-adventure-level';
  var POSITIONS = [0, 1, 2];
  var LEFT_PCT = ['0%', '50%', '100%'];

  function getSkin() {
    return localStorage.getItem(LS_SKIN) || 'cat';
  }

  function getLevel() {
    var v = parseInt(localStorage.getItem(LS_LEVEL), 10);
    return isNaN(v) ? 0 : Math.max(0, Math.min(2, v));
  }

  function isRTL(el) {
    if (document.dir === 'rtl') return true;
    var node = el;
    while (node) {
      if (node.dir === 'rtl') return true;
      node = node.parentElement;
    }
    return false;
  }

  function posToLeft(pos, rtl) {
    if (rtl) return LEFT_PCT[2 - pos];
    return LEFT_PCT[pos];
  }

  function leftToPos(pct, rtl) {
    var snapped = Math.round(pct / 50);
    snapped = Math.max(0, Math.min(2, snapped));
    return rtl ? 2 - snapped : snapped;
  }

  function getSkinData(lang, skin) {
    var skins = window.CC_SKINS;
    if (!skins) return null;
    var langData = skins[lang] || skins['en'];
    if (!langData) return null;
    return langData[skin] || langData['cat'] || null;
  }

  function initSlider(el) {
    var lang = el.getAttribute('data-lang') || 'en';
    var rtl = isRTL(el);

    var skinNameEl = el.querySelector('.slider-skin-name');
    var handle = el.querySelector('.slider-handle');
    var descEl = el.querySelector('#slider-desc') || el.querySelector('.slider-desc');
    var labelEls = el.querySelectorAll('.slider-label');

    if (!handle) return;

    var currentSkin = getSkin();
    var currentPos = getLevel();

    function render() {
      var data = getSkinData(lang, currentSkin);
      if (!data) return;

      if (skinNameEl) skinNameEl.textContent = data.name;

      handle.style.left = posToLeft(currentPos, rtl);
      handle.setAttribute('aria-valuenow', currentPos);

      labelEls.forEach(function (lbl) {
        var p = parseInt(lbl.getAttribute('data-position'), 10);
        lbl.textContent = data.positions[p] ? data.positions[p].label : '';
      });

      if (descEl) {
        var posData = data.positions[currentPos];
        descEl.textContent = posData ? posData.desc : '';
      }
    }

    function setPos(pos, save) {
      pos = Math.max(0, Math.min(2, pos));
      currentPos = pos;
      if (save !== false) {
        localStorage.setItem(LS_LEVEL, pos);
      }
      render();
      el.dispatchEvent(new CustomEvent('adventure-change', {
        bubbles: true,
        detail: { level: pos, skin: currentSkin, lang: lang }
      }));
    }

    function pctFromEvent(e, track) {
      var rect = track.getBoundingClientRect();
      var clientX = e.touches ? e.touches[0].clientX : e.clientX;
      var pct = ((clientX - rect.left) / rect.width) * 100;
      return Math.max(0, Math.min(100, pct));
    }

    var track = el.querySelector('.slider-track');

    // Mouse drag
    var dragging = false;
    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      dragging = true;
      handle.style.transition = 'none';
    });

    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      var pct = pctFromEvent(e, track);
      var pos = leftToPos(pct, rtl);
      currentPos = pos;
      handle.style.left = posToLeft(pos, rtl);
      handle.setAttribute('aria-valuenow', pos);
    });

    document.addEventListener('mouseup', function (e) {
      if (!dragging) return;
      dragging = false;
      handle.style.transition = '';
      var pct = pctFromEvent(e, track);
      setPos(leftToPos(pct, rtl));
    });

    // Touch drag
    handle.addEventListener('touchstart', function (e) {
      e.preventDefault();
      handle.style.transition = 'none';
    }, { passive: false });

    handle.addEventListener('touchmove', function (e) {
      e.preventDefault();
      var pct = pctFromEvent(e, track);
      var pos = leftToPos(pct, rtl);
      currentPos = pos;
      handle.style.left = posToLeft(pos, rtl);
      handle.setAttribute('aria-valuenow', pos);
    }, { passive: false });

    handle.addEventListener('touchend', function (e) {
      handle.style.transition = '';
      var pct = pctFromEvent(e.changedTouches[0] ? { clientX: e.changedTouches[0].clientX } : e, track);
      setPos(leftToPos(pct, rtl));
    });

    // Track click
    track.addEventListener('click', function (e) {
      if (e.target === handle) return;
      var pct = pctFromEvent(e, track);
      setPos(leftToPos(pct, rtl));
    });

    // Keyboard
    handle.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
        e.preventDefault();
        setPos(rtl ? currentPos - 1 : currentPos + 1);
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
        e.preventDefault();
        setPos(rtl ? currentPos + 1 : currentPos - 1);
      }
    });

    // Skin change from external
    window.addEventListener('skin-change', function () {
      currentSkin = getSkin();
      render();
    });

    render();

    // Store reference for setSkin
    el._sliderLang = lang;
    el._sliderSetSkin = function (skin) {
      currentSkin = skin;
      render();
    };
  }

  function init() {
    if (!window.CC_SKINS) {
      console.error('[adventure-slider] window.CC_SKINS not loaded — aborting');
      return;
    }

    var sliders = document.querySelectorAll('.adventure-slider');
    sliders.forEach(function (el) {
      initSlider(el);
    });
  }

  // Expose global setSkin
  window.CC_setSkin = function (skinName) {
    localStorage.setItem(LS_SKIN, skinName);
    var sliders = document.querySelectorAll('.adventure-slider');
    sliders.forEach(function (el) {
      if (el._sliderSetSkin) el._sliderSetSkin(skinName);
    });
    window.dispatchEvent(new CustomEvent('skin-change', { detail: { skin: skinName } }));
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
