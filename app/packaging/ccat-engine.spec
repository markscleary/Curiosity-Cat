# PyInstaller spec for the `ccat-engine` sidecar binary (APP-6).
#
# Builds curiosity_cat.serve:main (the same entry point as the
# `ccat-engine` console script in pyproject.toml) as a single-file
# executable that Tauri's `externalBin` spawns in place of the
# dev-mode "look up ccat-engine on PATH" path in src-tauri/src/sidecar.rs.
#
# Build (from repo root, using a venv with `pip install -e .` +
# `pip install pyinstaller` — see app/packaging/build-sidecar.sh):
#   pyinstaller app/packaging/ccat-engine.spec --distpath app/packaging/dist --workpath app/packaging/build
#
# Output: app/packaging/dist/ccat-engine (onefile binary). The build
# script then copies it into app/src-tauri/binaries/ with the
# target-triple suffix Tauri's externalBin convention requires.

import pathlib

REPO_ROOT = pathlib.Path(SPECPATH).resolve().parent.parent

a = Analysis(
    [str(REPO_ROOT / "app" / "packaging" / "ccat_engine_entry.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[
        (str(REPO_ROOT / "curiosity_cat" / "data"), "curiosity_cat/data"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # mcp_server.py (the optional `curiosity-cat-mcp` entry point) is never
    # imported by serve.py's call graph, so `mcp`/`pydantic` are excluded
    # rather than bundled — they aren't installed in the build venv either.
    excludes=["mcp", "pydantic"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ccat-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windows_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
