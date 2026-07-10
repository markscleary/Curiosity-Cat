// Curiosity Cat — app shell skin data. Ported from site/js/skins.js; v1
// ships the base "cat" skin only. Skin unlocks (site/js/skins.js's full
// set + skin-unlocker.js) are the APP-5 character-systems layer.
window.CC_SKINS = {
  en: {
    cat: {
      name: "Cat",
      positions: [
        { label: "Housecat", color: "#22c55e", desc: "Stay close to home. Standing orders active. Nothing leaves the yard." },
        { label: "Alley Cat", color: "#d97706", desc: "Calculated risks accepted. Braver exploration. Still comes home." },
        { label: "Tiger", color: "#b45309", desc: "Widest range. Explores the edge. Reports back – rare places and tales of danger." }
      ]
    }
  }
};

// Position index -> engine level string (curiosity_cat.core.LEVELS).
window.CC_LEVELS = ["housecat", "alleycat", "tiger"];
