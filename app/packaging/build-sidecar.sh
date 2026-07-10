#!/usr/bin/env bash
# Builds the ccat-engine PyInstaller sidecar and drops it into
# app/src-tauri/binaries/ with the target-triple suffix Tauri's
# `externalBin` convention requires (see tauri.conf.json bundle.externalBin
# and https://v2.tauri.app/develop/sidecar/).
#
# Usage: app/packaging/build-sidecar.sh
# Requires: python3, and app/packaging/.build-venv will be created on first
# run with `pip install -e .` + `pip install pyinstaller`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_VENV="$REPO_ROOT/app/packaging/.build-venv"
BINARIES_DIR="$REPO_ROOT/app/src-tauri/binaries"

if [ ! -d "$BUILD_VENV" ]; then
  echo "==> Creating sidecar build venv"
  python3 -m venv "$BUILD_VENV"
  "$BUILD_VENV/bin/pip" install --upgrade pip -q
  "$BUILD_VENV/bin/pip" install -e "$REPO_ROOT" -q
  "$BUILD_VENV/bin/pip" install pyinstaller -q
fi

echo "==> Running PyInstaller"
"$BUILD_VENV/bin/pyinstaller" "$REPO_ROOT/app/packaging/ccat-engine.spec" \
  --distpath "$REPO_ROOT/app/packaging/dist" \
  --workpath "$REPO_ROOT/app/packaging/build" \
  --noconfirm

TARGET_TRIPLE="$(rustc -vV | sed -n 's/host: //p')"
if [ -z "$TARGET_TRIPLE" ]; then
  echo "error: could not determine target triple from 'rustc -vV'" >&2
  exit 1
fi

mkdir -p "$BINARIES_DIR"
DEST="$BINARIES_DIR/ccat-engine-$TARGET_TRIPLE"
cp "$REPO_ROOT/app/packaging/dist/ccat-engine" "$DEST"
chmod +x "$DEST"

echo "==> Sidecar binary ready: $DEST"
"$DEST" serve <<< '{"id":1,"method":"status","params":{}}'
