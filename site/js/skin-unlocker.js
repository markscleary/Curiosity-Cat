// Curiosity Cat — Skin Unlocker

(function () {
  'use strict';

  var LS_UNLOCKED = 'curiosity-cat-unlocked-skins';
  var LS_SKIN = 'curiosity-cat-current-skin';

  var TIER_RAT_PCT = 50;
  var TIER_LANG_PCT = 90;

  var ratUnlocked = false;
  var langUnlocked = false;
  var scrollTimer = null;

  function getUnlocked() {
    try {
      var raw = localStorage.getItem(LS_UNLOCKED);
      return raw ? JSON.parse(raw) : ['cat'];
    } catch (e) {
      return ['cat'];
    }
  }

  function saveUnlocked(list) {
    localStorage.setItem(LS_UNLOCKED, JSON.stringify(list));
  }

  function getLang() {
    var el = document.querySelector('.adventure-slider');
    return el ? (el.getAttribute('data-lang') || 'en') : 'en';
  }

  function getLangAnimal(lang) {
    return window.CC_LANGUAGE_ANIMALS ? (window.CC_LANGUAGE_ANIMALS[lang] || null) : null;
  }

  function showToast(message) {
    var toast = document.createElement('div');
    toast.className = 'skin-unlock-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function () { toast.classList.add('visible'); }, 100);
    setTimeout(function () { toast.classList.remove('visible'); }, 3100);
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 3400);
  }

  function unlockSkin(skinName, lang) {
    var unlocked = getUnlocked();
    if (unlocked.indexOf(skinName) !== -1) return;

    unlocked.push(skinName);
    saveUnlocked(unlocked);

    if (window.CC_setSkin) {
      window.CC_setSkin(skinName);
    }

    if (window.CC_SKINS && window.CC_SKINS[lang] && window.CC_SKINS[lang][skinName]) {
      showToast(window.CC_SKINS[lang][skinName].unlockMessage);
    }
  }

  function getScrollPct() {
    var doc = document.documentElement;
    var scrolled = doc.scrollTop || document.body.scrollTop;
    var total = doc.scrollHeight - doc.clientHeight;
    if (total <= 0) return 100;
    return (scrolled / total) * 100;
  }

  function checkScrollTiers(lang, langAnimal) {
    var pct = getScrollPct();

    if (!ratUnlocked && pct >= TIER_RAT_PCT) {
      ratUnlocked = true;
      unlockSkin('rat', lang);
    }

    if (!langUnlocked && langAnimal && pct >= TIER_LANG_PCT) {
      langUnlocked = true;
      unlockSkin(langAnimal, lang);
    }
  }

  function onFaqClick(lang, langAnimal) {
    if (!langUnlocked && langAnimal) {
      langUnlocked = true;
      unlockSkin(langAnimal, lang);
    }
  }

  function highestSkin(unlocked, langAnimal) {
    if (langAnimal && unlocked.indexOf(langAnimal) !== -1) return langAnimal;
    if (unlocked.indexOf('rat') !== -1) return 'rat';
    return 'cat';
  }

  function init() {
    var lang = getLang();
    var langAnimal = getLangAnimal(lang);
    var unlocked = getUnlocked();

    ratUnlocked = unlocked.indexOf('rat') !== -1;
    langUnlocked = langAnimal ? unlocked.indexOf(langAnimal) !== -1 : true;

    // Start on highest unlocked skin
    var best = highestSkin(unlocked, langAnimal);
    localStorage.setItem(LS_SKIN, best);

    // Scroll listener
    window.addEventListener('scroll', function () {
      if (scrollTimer) return;
      scrollTimer = setTimeout(function () {
        scrollTimer = null;
        checkScrollTiers(lang, langAnimal);
      }, 100);
    }, { passive: true });

    // FAQ click listener
    var faqEls = document.querySelectorAll('details, .faq-item');
    faqEls.forEach(function (el) {
      el.addEventListener('click', function () {
        onFaqClick(lang, langAnimal);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
