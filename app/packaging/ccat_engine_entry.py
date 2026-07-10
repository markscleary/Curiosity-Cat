"""PyInstaller entry point for the ccat-engine sidecar binary.

Tauri's externalBin spawns the built binary with a `serve` argv, matching
`curiosity_cat.serve.main()`'s own argparse contract (see serve.py) — this
module just gives PyInstaller a script to analyze, since the real console
script is a pyproject.toml `[project.scripts]` entry point, not a file.
"""

from curiosity_cat.serve import main

if __name__ == "__main__":
    main()
