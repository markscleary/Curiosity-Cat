# Draft Homebrew cask (APP-6) — not yet published to any tap.
#
# Intended home: a personal tap, e.g. `markscleary/homebrew-curiosity-cat`,
# installed via `brew tap markscleary/curiosity-cat && brew install --cask
# curiosity-cat`. Requires a tagged GitHub release with the DMG this repo's
# `cargo tauri build` produces (`app/src-tauri/target/release/bundle/dmg/`)
# uploaded as a release asset — see docs/app/SIGNING.md for the signed
# build this should point at once Mark's Apple Developer ID lands; an
# ad-hoc/unsigned DMG will Gatekeeper-block on install for anyone who isn't
# the machine that built it.
#
# GitHub renames spaces to periods in uploaded release asset filenames, so
# the on-disk build name ("Curiosity Cat_0.1.0_aarch64.dmg") becomes the
# download URL below ("Curiosity.Cat_...").
#
# Before publishing a release, replace REPLACE_WITH_SHA256_OF_RELEASED_DMG
# with the real digest: `shasum -a 256 "Curiosity Cat_<version>_aarch64.dmg"`.
# Apple Silicon only for v1 — no Intel build exists yet (this machine is an
# M4 Pro); add an `on_intel`/`on_arm` split if/when an x86_64 build ships.

cask "curiosity-cat" do
  version "0.1.0"
  sha256 "REPLACE_WITH_SHA256_OF_RELEASED_DMG"

  url "https://github.com/markscleary/Curiosity-Cat/releases/download/app-v#{version}/Curiosity.Cat_#{version}_aarch64.dmg",
      verified: "github.com/markscleary/Curiosity-Cat/"
  name "Curiosity Cat"
  desc "Menu bar companion that watches your coding agent, explains what it just did in one plain sentence, and holds anything irreversible for your yes/no"
  homepage "https://curiositycat.online"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: ">= :monterey"

  app "Curiosity Cat.app"

  zap trash: [
    "~/Library/Application Support/online.curiositycat.shell",
    "~/Library/Caches/online.curiositycat.shell",
    "~/Library/Saved Application State/online.curiositycat.shell.savedState",
    "~/Library/WebKit/online.curiositycat.shell",
  ]
end
