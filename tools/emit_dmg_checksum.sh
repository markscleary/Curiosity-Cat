#!/usr/bin/env bash
# Emit the SHA-256 of the built Curiosity Cat .dmg for the /download page
# and the Homebrew cask. Read-only: hashes an existing artifact, writes a
# sidecar SHA256SUMS file, prints copy-paste-ready lines. No build, no sign.
#
# IMPORTANT: the value published on /download and in the cask must be the
# hash of the SIGNED + NOTARISED + STAPLED dmg (signing changes bytes).
# Until Mark's Developer ID cert + notary credential land (see
# tools/sign_and_notarize.sh), this emits a PROVISIONAL digest of the
# current unsigned build — clearly labelled as such.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DMG_DIR="$REPO_ROOT/app/src-tauri/target/release/bundle/dmg"
DMG="${1:-$(ls "$DMG_DIR/"*.dmg 2>/dev/null | head -1 || true)}"

if [ -z "${DMG:-}" ] || [ ! -f "$DMG" ]; then
  echo "no .dmg found in $DMG_DIR — run 'cd app && npx --yes @tauri-apps/cli@2 build' first" >&2
  exit 2
fi

# adhoc/unsigned builds are provisional; a notarised build has a Developer ID authority
SIGNED="provisional (unsigned/adhoc build)"
if /usr/bin/codesign -dv --verbose=4 "$DMG" 2>&1 | grep -q 'Authority=Developer ID'; then
  SIGNED="final (Developer ID signed)"
fi

DIGEST="$(shasum -a 256 "$DMG" | awk '{print $1}')"
BASENAME="$(basename "$DMG")"

# write a sidecar checksums file next to the dmg
printf '%s  %s\n' "$DIGEST" "$BASENAME" > "$DMG_DIR/SHA256SUMS"

echo "dmg      : $DMG"
echo "status   : $SIGNED"
echo "sha256   : $DIGEST"
echo "wrote    : $DMG_DIR/SHA256SUMS"
echo
echo "# Homebrew cask (app/packaging/homebrew/curiosity-cat.rb):"
echo "  sha256 \"$DIGEST\""
echo
echo "# /download page snippet:"
echo "  SHA-256 ($BASENAME): $DIGEST"
[ "$SIGNED" = "final (Developer ID signed)" ] || echo "  (PROVISIONAL — re-run on the notarised dmg before publishing.)"
