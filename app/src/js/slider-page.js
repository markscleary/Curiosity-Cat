(function () {
  'use strict';

  var sliderEl = document.querySelector('.adventure-slider');
  var compileBtn = document.getElementById('compile-btn');
  var statusEl = document.getElementById('status');
  var territoryDiagramEl = document.getElementById('territory-diagram');
  var profileCard = document.getElementById('profile-card');
  var profileMdEl = document.getElementById('profile-md');
  var whatcanPanelEl = document.getElementById('whatcan-panel');

  var selectedLevel = window.CC_LEVELS[0];

  window.CCAT_initSlider(sliderEl, 0, function (_pos, level) {
    selectedLevel = level;
    window.CCAT_renderTerritoryDiagram(territoryDiagramEl, selectedLevel);
  });
  window.CCAT_renderTerritoryDiagram(territoryDiagramEl, selectedLevel);

  compileBtn.addEventListener('click', function () {
    compileBtn.disabled = true;
    statusEl.textContent = 'Compiling ' + selectedLevel + ' profile…';
    profileCard.hidden = true;

    window.CCAT.compile(selectedLevel, 'claude-code')
      .then(function (profileDir) {
        statusEl.textContent = 'Compiled to ' + profileDir.path;
        return window.CCAT.setLastProfileDir(profileDir.path).then(function () {
          return window.CCAT.readTextFile(profileDir.profile_md_path);
        });
      })
      .then(function (profileMd) {
        profileMdEl.textContent = profileMd;
        window.CCAT_renderWhatCanDo(whatcanPanelEl, profileMd);
        profileCard.hidden = false;
      })
      .catch(function (err) {
        statusEl.textContent = 'Compile failed: ' + err;
      })
      .finally(function () {
        compileBtn.disabled = false;
      });
  });
})();
