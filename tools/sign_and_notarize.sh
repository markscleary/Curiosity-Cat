#!/usr/bin/env bash
# Curiosity Cat — codesign + notarytool DRY RUN.
#
# Non-destructive by default: prints the EXACT command sequence that will
# sign and notarise the release build, with real values (identity, team id,
# paths) filled in — but runs nothing that signs or uploads. It also runs
# read-only diagnostics of the current signing state, and names precisely
# what is still blocked on Mark (a human-only grant) so his one sitting is
# minutes, not an afternoon.
#
# Implements docs/app/SIGNING.md sections 1-6. Nothing here uploads to Apple
# or touches Mark's keys; codesign only runs under the explicit
# --run-codesign opt-in, and even then never notarises (no submit).
#
# Usage:
#   tools/sign_and_notarize.sh                # dry run: print + diagnose
#   tools/sign_and_notarize.sh --run-codesign # also sign locally IF a
#                                             # Developer ID identity exists
#                                             # (still no upload)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$REPO_ROOT/app/src-tauri/target/release/bundle/macos/Curiosity Cat.app"
SIDECAR="$APP/Contents/MacOS/ccat-engine"
ENTITLEMENTS="$REPO_ROOT/app/src-tauri/Entitlements.plist"
DMG="$(ls "$REPO_ROOT/app/src-tauri/target/release/bundle/dmg/"*.dmg 2>/dev/null | head -1 || true)"

RUN_CODESIGN=0
[ "${1:-}" = "--run-codesign" ] && RUN_CODESIGN=1

hr(){ printf '%s\n' "------------------------------------------------------------"; }
say(){ printf '%s\n' "$*"; }

say "Curiosity Cat — signing/notarisation dry run"
hr
say "app bundle  : $APP"
say "sidecar     : $SIDECAR"
say "dmg         : ${DMG:-<none built yet>}"
say "entitlements: $ENTITLEMENTS"
[ -d "$APP" ] || say "!! no built .app — run 'cd app && npx --yes @tauri-apps/cli@2 build' first"
[ -f "$ENTITLEMENTS" ] || { say "!! missing $ENTITLEMENTS"; exit 2; }

TEAM_ID="${APPLE_TEAM_ID:-}"
if [ -z "$TEAM_ID" ] && [ -f "$REPO_ROOT/APPLE_DEVELOPER.md" ]; then
  TEAM_ID="$(grep -Eo 'Team ID:[[:space:]]*[A-Z0-9]+' "$REPO_ROOT/APPLE_DEVELOPER.md" | awk '{print $NF}' | head -1 || true)"
fi
say "team id     : ${TEAM_ID:-<unknown — set APPLE_TEAM_ID>}"
hr

BLOCKED=0
IDENTITY="$(security find-identity -v -p codesigning 2>/dev/null | grep 'Developer ID Application' | head -1 | sed -E 's/^[[:space:]]*[0-9]+\)[[:space:]]*[0-9A-F]+[[:space:]]*"(.*)"$/\1/' || true)"
if [ -z "$IDENTITY" ]; then
  BLOCKED=1
  IDENTITY="Developer ID Application: Mark Cleary (${TEAM_ID:-TEAMID})"
  say "SIGNING IDENTITY: none installed."
  say "  blocked-on-Mark:signing-identity"
  say "  Fix (SIGNING.md step 1): Xcode > Settings > Accounts > team >"
  say "  Manage Certificates > + > Developer ID Application. Then re-run."
  say "  (placeholder used below for the dry run: \"$IDENTITY\")"
else
  say "SIGNING IDENTITY: $IDENTITY"
fi
hr

NOTARY_READY=0
if [ -n "${APPLE_API_KEY:-}" ] && [ -n "${APPLE_API_KEY_ID:-}" ] && [ -n "${APPLE_API_ISSUER:-}" ]; then
  NOTARY_READY=1; say "NOTARY CREDENTIAL: App Store Connect API key present (env)."
elif [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_PASSWORD:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ]; then
  NOTARY_READY=1; say "NOTARY CREDENTIAL: app-specific password present (env)."
else
  BLOCKED=1
  say "NOTARY CREDENTIAL: none in env."
  say "  blocked-on-Mark:notary-credential"
  say "  Fix (SIGNING.md step 3): app-specific password at appleid.apple.com,"
  say "  or an App Store Connect API key; export the env vars it lists."
  say "  (Never store these in files — Keychain / CI secrets only.)"
fi
hr

say "CURRENT STATE (read-only):"
if [ -d "$APP" ]; then
  codesign -dv --verbose=4 "$APP" 2>&1 | grep -Ei 'flags|TeamIdentifier|Identifier=|Authority' || true
  say "spctl assessment:"
  /usr/sbin/spctl --assess --type execute -vv "$APP" 2>&1 || true
fi
hr

say "PLANNED COMMAND SEQUENCE (inside-out sign, then notarise, then staple):"
say ""
say "# 1. sign the sidecar first (nested code before the outer app)"
CS_SIDECAR=(codesign --force --options runtime --timestamp --entitlements "$ENTITLEMENTS" --sign "$IDENTITY" "$SIDECAR")
printf '   %q ' "${CS_SIDECAR[@]}"; echo
say ""
say "# 2. sign the app bundle"
CS_APP=(codesign --force --options runtime --timestamp --entitlements "$ENTITLEMENTS" --sign "$IDENTITY" "$APP")
printf '   %q ' "${CS_APP[@]}"; echo
say ""
say "# 3. verify the signature (read-only)"
say "   codesign --verify --deep --strict --verbose=2 \"$APP\""
say ""
say "# 4. notarise the dmg and WAIT (this is the upload — never run by this script)"
say "   xcrun notarytool submit \"${DMG:-<dmg>}\" --apple-id \"\$APPLE_ID\" --password \"\$APPLE_PASSWORD\" --team-id \"\$APPLE_TEAM_ID\" --wait"
say "   # or API-key form:"
say "   xcrun notarytool submit \"${DMG:-<dmg>}\" --key \"\$APPLE_API_KEY\" --key-id \"\$APPLE_API_KEY_ID\" --issuer \"\$APPLE_API_ISSUER\" --wait"
say ""
say "# 5. staple the ticket so Gatekeeper works offline"
say "   xcrun stapler staple \"${DMG:-<dmg>}\" && xcrun stapler validate \"${DMG:-<dmg>}\""
hr

if [ "$RUN_CODESIGN" -eq 1 ]; then
  if ! security find-identity -v -p codesigning 2>/dev/null | grep -q 'Developer ID Application'; then
    say "--run-codesign requested but no Developer ID identity is installed — refusing."
    say "blocked-on-Mark:signing-identity"
    exit 3
  fi
  say "--run-codesign: signing locally (NO upload)…"
  [ -f "$SIDECAR" ] && "${CS_SIDECAR[@]}"
  "${CS_APP[@]}"
  codesign --verify --deep --strict --verbose=2 "$APP"
  say "local signing done. Notarisation still requires the two steps above."
else
  say "DRY RUN only — nothing signed or uploaded. Re-run with --run-codesign"
  say "once the Developer ID cert is installed to sign locally (still no upload)."
fi

if [ "$BLOCKED" -eq 1 ]; then
  say ""
  say "SUMMARY: blocked on Mark for one sitting — see the blocked-on-Mark lines"
  say "above and docs/app/SIGNING.md. Everything else is prepared."
  exit 3
fi
say ""
say "SUMMARY: prerequisites present. Ready to sign + notarise per the sequence."
