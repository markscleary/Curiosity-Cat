// Curiosity Cat — app shell skin data. Ported from site/js/skins.js's
// en locale (APP-S1): the full seven-species set, for the Settings
// window's skin selector (app/src/js/settings-store.js owns which of
// these are unlocked). Translations (ar/zh/hi in the site version) are a
// future i18n layer — the app shell has no language switcher yet, and
// adventure-slider.js still reads skins.en.<name> directly.
window.CC_SKINS = {
  en: {
    cat: {
      name: "Cat",
      positions: [
        { label: "Housecat", color: "#22c55e", desc: "Stay close to home. Standing orders active. Nothing leaves the yard." },
        { label: "Alley Cat", color: "#d97706", desc: "Calculated risks accepted. Braver exploration. Still comes home." },
        { label: "Tiger", color: "#b45309", desc: "Widest range. Explores the edge. Reports back – rare places and tales of danger." }
      ]
    },
    puppy: {
      name: "Puppy",
      positions: [
        { label: "Puppy", color: "#22c55e", desc: "On the leash. Close to home. Trained behaviours only." },
        { label: "Yard Dog", color: "#d97706", desc: "Off the leash in the yard. Curious. Comes when called." },
        { label: "Wolf", color: "#b45309", desc: "Wide-ranging. Hunts alone. Reports back." }
      ]
    },
    rat: {
      name: "Rat",
      positions: [
        { label: "Lab Rat", color: "#22c55e", desc: "Controlled conditions. Every run mapped. Nothing unexpected." },
        { label: "Street Rat", color: "#d97706", desc: "Out in the world. Smart about the route. Avoids the traps." },
        { label: "King Rat", color: "#b45309", desc: "First through the tunnel. Finds what the others missed." }
      ]
    },
    camel: {
      name: "Camel",
      positions: [
        { label: "Pet Camel", color: "#22c55e", desc: "Stabled. Fed by hand. Knows the paddock." },
        { label: "Trail Camel", color: "#d97706", desc: "On the caravan route. Calculated trips. Returns to water." },
        { label: "Dune Racer", color: "#b45309", desc: "Off the route. Beyond the last well. Brings back the map." }
      ]
    },
    panda: {
      name: "Panda",
      positions: [
        { label: "Baby Panda", color: "#22c55e", desc: "Close to the enclosure. Watched at every step." },
        { label: "Forest Panda", color: "#d97706", desc: "In the reserve. Wider territory. Still monitored." },
        { label: "Wild Panda", color: "#b45309", desc: "Mountain range. Own decisions. Rare sightings." }
      ]
    },
    primate: {
      name: "Primate",
      positions: [
        { label: "Marmoset", color: "#22c55e", desc: "Treetops only. Small territory. Predictable." },
        { label: "Macaque", color: "#d97706", desc: "Streets and temples. Takes what is offered. Street-smart." },
        { label: "Gorilla", color: "#b45309", desc: "Deep forest. Sets its own path. What it finds, no one else does." }
      ]
    },
    cobra: {
      name: "Cobra",
      positions: [
        { label: "Garden Cobra", color: "#22c55e", desc: "Familiar ground. Coiled. Warning first." },
        { label: "Forest Cobra", color: "#d97706", desc: "Further out. Rising. Tracks what moves." },
        { label: "King Cobra", color: "#b45309", desc: "Apex. Strikes when it chooses. Brings back what it learns." }
      ]
    }
  }
};

// Position index -> engine level string (curiosity_cat.core.LEVELS).
window.CC_LEVELS = ["housecat", "alleycat", "tiger"];
