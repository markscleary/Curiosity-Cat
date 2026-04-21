// Curiosity Cat — Skin definitions
// Adventure slider metadata for each species skin.
// Multi-language support added incrementally.

window.CC_SKINS = {
  en: {
    cat: {
      name: "Cat",
      unlockMessage: "New skin unlocked: Rat",
      positions: [
        { label: "Housecat", color: "#22c55e", desc: "Stay close to home. Standing orders enforced. Nothing leaves the yard." },
        { label: "Alley Cat", color: "#d97706", desc: "Calculated risks accepted. Braver exploration. Still comes home." },
        { label: "Tiger", color: "#b45309", desc: "Widest range. Explores the edge. Reports back – rare places and tales of danger." }
      ]
    },
    puppy: {
      name: "Puppy",
      unlockMessage: "New skin unlocked: Puppy",
      positions: [
        { label: "Puppy", color: "#22c55e", desc: "On the leash. Close to home. Trained behaviours only." },
        { label: "Yard Dog", color: "#d97706", desc: "Off the leash in the yard. Curious. Comes when called." },
        { label: "Wolf", color: "#b45309", desc: "Wide-ranging. Hunts alone. Reports back." }
      ]
    },
    rat: {
      name: "Rat",
      unlockMessage: "New skin unlocked: Rat",
      positions: [
        { label: "Lab Rat", color: "#22c55e", desc: "Controlled conditions. Every run mapped. Nothing unexpected." },
        { label: "Street Rat", color: "#d97706", desc: "Out in the world. Smart about the route. Avoids the traps." },
        { label: "King Rat", color: "#b45309", desc: "First through the tunnel. Finds what the others missed." }
      ]
    },
    camel: {
      name: "Camel",
      unlockMessage: "New skin unlocked: Camel",
      positions: [
        { label: "Pet Camel", color: "#22c55e", desc: "Stabled. Fed by hand. Knows the paddock." },
        { label: "Trail Camel", color: "#d97706", desc: "On the caravan route. Calculated trips. Returns to water." },
        { label: "Dune Racer", color: "#b45309", desc: "Off the route. Beyond the last well. Brings back the map." }
      ]
    },
    panda: {
      name: "Panda",
      unlockMessage: "New skin unlocked: Panda",
      positions: [
        { label: "Baby Panda", color: "#22c55e", desc: "Close to the enclosure. Watched at every step." },
        { label: "Forest Panda", color: "#d97706", desc: "In the reserve. Wider territory. Still monitored." },
        { label: "Wild Panda", color: "#b45309", desc: "Mountain range. Own decisions. Rare sightings." }
      ]
    },
    primate: {
      name: "Primate",
      unlockMessage: "New skin unlocked: Primate",
      positions: [
        { label: "Marmoset", color: "#22c55e", desc: "Treetops only. Small territory. Predictable." },
        { label: "Macaque", color: "#d97706", desc: "Streets and temples. Takes what's offered. Street-smart." },
        { label: "Gorilla", color: "#b45309", desc: "Deep forest. Sets its own path. What it finds, no one else does." }
      ]
    },
    cobra: {
      name: "Cobra",
      unlockMessage: "New skin unlocked: Cobra",
      positions: [
        { label: "Garden Cobra", color: "#22c55e", desc: "Familiar ground. Coiled. Warning first." },
        { label: "Forest Cobra", color: "#d97706", desc: "Further out. Rising. Tracks what moves." },
        { label: "King Cobra", color: "#b45309", desc: "Apex. Strikes when it chooses. Brings back what it learns." }
      ]
    }
  }
};

// Language-to-unlocked-animal mapping
window.CC_LANGUAGE_ANIMALS = {
  en: null,   // English stays with cat+rat as the reward
  ar: "camel",
  zh: "panda",
  hi: "cobra",
  ta: "primate"
};
