# The Package That Typos

**Threat class:** package
**Severity:** bitten
**Framework:** Claude Code
**Adventure level:** alleycat

Asked my agent to add colour formatting to a Python CLI tool. It ran pip install colourma — one letter off from colorama. The typosquat package existed. It installed cleanly. No errors.

The agent even tested it and got an import error, which it tried to debug by reading the package source. That's when it found the setup.py had a post-install hook that wrote a cron job to ~/.local/bin. The cron job curled a payload every six hours.

Standing orders caught it at the "reading unfamiliar package source" step — flagged the shell commands in setup.py as suspicious executable content. But the package was already installed. Had to nuke the venv and audit the cron directory.

**Lesson:** Typosquatting works because agents don't double-check spelling. Verify package names against PyPI/npm before installing. One letter is all it takes.
