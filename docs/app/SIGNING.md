# Signing & notarisation — the APP-6 gate

Everything distribution-shaped that does *not* need Apple credentials is
done: the PyInstaller `ccat-engine` sidecar, the unsigned/ad-hoc release
build (`.app` + `.dmg`, `app/README.md` "Building"), the draft Homebrew
cask (`app/packaging/homebrew/curiosity-cat.rb`), and the updater config
pointed at GitHub Releases (`app/src-tauri/tauri.conf.json`
`plugins.updater`). This doc is everything left, gated on Mark having an
active Apple Developer Program membership (`docs/app/APP_SPEC.md` HUMAN
DEPENDENCIES) — ready to run in order, nothing left to figure out.

Today's unsigned build is ad-hoc signed by Tauri automatically
(`codesign -dv` on the built `.app` shows `flags=0x20002(adhoc,linker-signed)`,
`TeamIdentifier=not set`). That's enough to run on the machine that built
it; it is not enough to distribute — Gatekeeper blocks an ad-hoc/unsigned
app on any other Mac with an "is damaged and can't be opened" or
"unidentified developer" prompt, and `brew install --cask` will hit the
same wall (see the cask file's comment).

## 0. Prerequisites checklist

- [ ] Active Apple Developer Program membership ($99/yr, enrolled at
      https://developer.apple.com/account — this is the one paid,
      human-only step everything below depends on)
- [ ] Xcode or just Xcode Command Line Tools installed (`xcode-select --install`)
      — needed for `codesign`, `xcrun notarytool`, `xcrun stapler`
- [ ] Signed in to the Apple ID with that membership in Xcode
      (Xcode → Settings → Accounts), or willing to create the cert via
      the web portal + Keychain Access CSR instead

## 1. Get a "Developer ID Application" certificate

Easiest path (Xcode installed, signed into the account):

```sh
xcodebuild -exportNotarizedApp 2>/dev/null  # no-op, just confirms Xcode CLI is present
```

Actually create the cert:

1. Xcode → Settings → Accounts → select the team → Manage Certificates →
   "+" → **Developer ID Application**. Xcode creates the CSR, requests the
   cert, and installs it into the login keychain in one step.
2. Confirm it landed:
   ```sh
   security find-identity -v -p codesigning
   ```
   Look for a line like:
   ```
   1) ABCDEF0123456789ABCDEF0123456789ABCDEF01 "Developer ID Application: Mark Cleary (TEAMID1234)"
   ```
   Copy that quoted string — it's the signing identity.

(No Xcode: developer.apple.com → Certificates, Identifiers & Profiles →
Certificates → "+" → Developer ID Application, upload a CSR generated via
Keychain Access → Certificate Assistant → Request a Certificate from a
Certificate Authority, then double-click the downloaded `.cer` to install
it into the login keychain.)

## 2. Point Tauri at the identity

Add to `app/src-tauri/tauri.conf.json`'s `bundle.macOS`:

```json
"macOS": {
  "minimumSystemVersion": "12.0",
  "signingIdentity": "Developer ID Application: Mark Cleary (TEAMID1234)"
}
```

or skip the config edit and set an env var per build instead (useful for
CI, where the identity string shouldn't be hardcoded):

```sh
export APPLE_SIGNING_IDENTITY="Developer ID Application: Mark Cleary (TEAMID1234)"
```

## 3. Get an app-specific password (or API key) for notarisation

App-specific password (simplest for a one-person, local-build workflow):

1. https://appleid.apple.com → Sign-In and Security → App-Specific
   Passwords → generate one, label it e.g. "curiosity-cat notarytool".
2. Set the three env vars `tauri build` reads:
   ```sh
   export APPLE_ID="curiositycat@shortandsweet.org"
   export APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx"   # the app-specific password, not the Apple ID password
   export APPLE_TEAM_ID="TEAMID1234"
   ```

API key instead (better for CI — doesn't expire on password rotation):

1. https://appstoreconnect.apple.com/access/api → Keys → generate one
   with the **Developer** role, download the `.p8` (only downloadable
   once).
2. Set:
   ```sh
   export APPLE_API_KEY="/path/to/AuthKey_XXXXXXXXXX.p8"
   export APPLE_API_ISSUER="issuer-uuid-from-the-same-page"
   export APPLE_API_KEY_ID="XXXXXXXXXX"   # the key ID in the filename
   ```

Either credential set is sufficient — Tauri's bundler picks whichever is
present, API key first.

## 4. Build, sign, and notarise in one step

With step 2's identity and step 3's credentials exported:

```sh
cd app
npx --yes @tauri-apps/cli@2 build   # NOT --debug — notarisation only runs on release builds
```

Tauri codesigns the `.app` (hardened runtime on by default for Developer
ID signing), submits the `.dmg` to `notarytool`, waits for approval, and
staples the ticket automatically — no separate commands needed. Confirm:

```sh
APP="app/src-tauri/target/release/bundle/macos/Curiosity Cat.app"
DMG="app/src-tauri/target/release/bundle/dmg/Curiosity Cat_0.1.0_aarch64.dmg"

codesign -dv --verbose=4 "$APP"          # TeamIdentifier should now be set
spctl --assess --type execute -vv "$APP" # should say "accepted", "source=Notarized Developer ID"
xcrun stapler validate "$DMG"            # should say "The validate action worked!"
```

## 5. Manual fallback (if the automatic flow needs debugging)

Exactly what Tauri's bundler runs under the hood, in case one step needs
to be diagnosed or re-run by hand against an already-built `.app`/`.dmg`:

```sh
IDENTITY="Developer ID Application: Mark Cleary (TEAMID1234)"
APP="app/src-tauri/target/release/bundle/macos/Curiosity Cat.app"
DMG="app/src-tauri/target/release/bundle/dmg/Curiosity Cat_0.1.0_aarch64.dmg"

# Sign (hardened runtime required for notarisation)
codesign --force --deep --options runtime --timestamp \
  --sign "$IDENTITY" "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

# Submit for notarisation and wait for a result (app-specific-password form)
xcrun notarytool submit "$DMG" \
  --apple-id "$APPLE_ID" --password "$APPLE_PASSWORD" --team-id "$APPLE_TEAM_ID" \
  --wait

# ...or the API-key form:
xcrun notarytool submit "$DMG" \
  --key "$APPLE_API_KEY" --key-id "$APPLE_API_KEY_ID" --issuer "$APPLE_API_ISSUER" \
  --wait

# Staple the notarisation ticket so Gatekeeper works fully offline
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"

# If a submission is rejected, see why:
xcrun notarytool log <submission-id> \
  --apple-id "$APPLE_ID" --password "$APPLE_PASSWORD" --team-id "$APPLE_TEAM_ID"
```

## 6. Entitlements — confirm, don't assume

`sidecar.rs` spawns `ccat-engine` as a plain child process (no XPC, no
network entitlement needed beyond what a regular process gets) and
`watcher.rs` spawns that same bundled binary a second time, in `listen`
mode (APP-BUILD-3). Tauri's default
`entitlements.plist` (hardened runtime, no extra entitlements) should
cover this, but unsigned/ad-hoc dev builds never exercise hardened-runtime
restrictions — verify once step 4 produces a real signed build:

```sh
codesign -d --entitlements :- "$APP"
"$APP/Contents/MacOS/curiosity-cat" &   # launch the signed build directly
# confirm ccat-engine still spawns as a child (ps aux | grep ccat-engine)
# and that the Watcher listener still binds 127.0.0.1:8377
```

If the sidecar fails to spawn only in the signed build (works ad-hoc,
fails notarised), that's almost always a missing
`com.apple.security.cs.allow-unsigned-executable-memory` or an
`allow-jit`-style entitlement PyInstaller's bootloader needs under the
hardened runtime — add it to
`app/src-tauri/Entitlements.plist` (new file) and point
`bundle.macOS.entitlements` at it in `tauri.conf.json`, then re-sign.

## 7. Updater signing key (separate from Apple credentials)

Not gated on Apple — can happen any time, but grouped here since it's the
other secret a real release needs. `app/src-tauri/tauri.conf.json`'s
`plugins.updater.pubkey` is currently the placeholder string
`REPLACE_WITH_TAURI_SIGNER_PUBLIC_KEY`, and `bundle.createUpdaterArtifacts`
is `false` (so routine unsigned builds, like the one this brief verified,
don't fail looking for a private key). Before the first real release:

```sh
cd app
npx --yes @tauri-apps/cli@2 signer generate -w ~/.tauri/curiosity-cat.key
```

This prints a public key — paste it into `tauri.conf.json`'s
`plugins.updater.pubkey`, flip `bundle.createUpdaterArtifacts` to `true`,
and keep `~/.tauri/curiosity-cat.key` (plus its password, if set) out of
git — it goes in CI secrets / a password manager, exported at build time
as `TAURI_SIGNING_PRIVATE_KEY` (file path or raw contents) and
`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`.

## 8. Release checklist (once 1–7 are done once)

1. Bump `version` in `app/src-tauri/tauri.conf.json`.
2. `app/packaging/build-sidecar.sh` (only if `curiosity_cat/serve.py` or
   its deps changed since the last release).
3. `cd app && npx --yes @tauri-apps/cli@2 build` with steps 2/3/7's env
   vars set — produces the signed, notarised, stapled `.dmg` plus the
   updater `.tar.gz`/`.sig`.
4. Tag and push (e.g. `app-v0.1.0`), create a GitHub release, upload the
   `.dmg`, the updater `.app.tar.gz`, its `.sig`, and a hand-built
   `latest.json` (or use `tauri-apps/tauri-action` in CI to generate it) —
   matching the URL pattern in `app/packaging/homebrew/curiosity-cat.rb`
   and `tauri.conf.json`'s `plugins.updater.endpoints`.
5. `shasum -a 256` the released `.dmg`, drop it into the cask file, open a
   PR against whatever tap it ends up living in.
