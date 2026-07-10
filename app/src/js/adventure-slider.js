// Curiosity Cat — Adventure Slider (app shell port of site/js/adventure-slider.js).
// Drag/click/keyboard behaviour is unchanged; localStorage persistence and
// multi-skin support are dropped since the app shell has one skin in v1
// and each window tracks its own selection explicitly.

(function () {
  'use strict';

  var POSITIONS = [0, 1, 2];
  var LEFT_PCT = ['0%', '50%', '100%'];

  function posToLeft(pos) {
    return LEFT_PCT[pos];
  }

  function leftToPos(pct) {
    var snapped = Math.round(pct / 50);
    return Math.max(0, Math.min(2, snapped));
  }

  function getSkinData() {
    var skins = window.CC_SKINS;
    if (!skins) return null;
    return skins.en.cat;
  }

  window.CCAT_initSlider = function initSlider(el, initialPos, onChange) {
    var skinNameEl = el.querySelector('.slider-skin-name');
    var handle = el.querySelector('.slider-handle');
    var descEl = el.querySelector('.slider-desc');
    var labelEls = el.querySelectorAll('.slider-label');
    var track = el.querySelector('.slider-track');

    if (!handle || !track) return;

    var currentPos = POSITIONS.indexOf(initialPos) >= 0 ? initialPos : 0;

    function render() {
      var data = getSkinData();
      if (!data) return;

      if (skinNameEl) skinNameEl.textContent = data.name;
      handle.style.left = posToLeft(currentPos);
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

    function setPos(pos) {
      pos = Math.max(0, Math.min(2, pos));
      currentPos = pos;
      render();
      if (onChange) onChange(pos, window.CC_LEVELS[pos]);
    }

    function pctFromEvent(e) {
      var rect = track.getBoundingClientRect();
      var clientX = e.touches ? e.touches[0].clientX : e.clientX;
      var pct = ((clientX - rect.left) / rect.width) * 100;
      return Math.max(0, Math.min(100, pct));
    }

    var dragging = false;
    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      dragging = true;
      handle.style.transition = 'none';
    });

    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      var pos = leftToPos(pctFromEvent(e));
      currentPos = pos;
      handle.style.left = posToLeft(pos);
      handle.setAttribute('aria-valuenow', pos);
    });

    document.addEventListener('mouseup', function (e) {
      if (!dragging) return;
      dragging = false;
      handle.style.transition = '';
      setPos(leftToPos(pctFromEvent(e)));
    });

    track.addEventListener('click', function (e) {
      if (e.target === handle) return;
      setPos(leftToPos(pctFromEvent(e)));
    });

    handle.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
        e.preventDefault();
        setPos(currentPos + 1);
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
        e.preventDefault();
        setPos(currentPos - 1);
      }
    });

    render();
    return {
      getPos: function () { return currentPos; },
      setPos: setPos
    };
  };
})();
