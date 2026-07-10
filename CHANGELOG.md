# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - 2026-07-11

### Added
- `curiosity-cat compile` — generates real Claude Code `settings.json` permission rules for a given adventure level and target, instead of hand-written policy templates.
- `curiosity-cat prove` — runs escape trials against a compiled profile's actual enforcement, with an observed-trials mode that replays the compiled `settings.json` rules against a sandbox seeded with them (not just self-consistency checks).

### Fixed
- Sandbox/deny bypass in the compiler: an invalid schema plus a bare catch-all deny rule could combine to let a call through unblocked.
- `curiosity-cat prove` now proves enforcement rather than validating the compiler's own output against itself.

### Changed
- Unified `threat_class` and `adventure_level` vocabulary across `schema.json` and the compiled policy templates so the compiler, the danger map, and the stories agree on the same terms.
- Honesty pass across docs and the website: flag/guide language now says explicitly where enforcement is unshipped versus where `compile`/`prove` back a claim.
- Surfaced ATLAS and NIST standards mapping on the stories, site, and API docs, anchoring Curiosity Cat's threat classes against those frameworks.
- Language refresh: English, Mandarin, Arabic, and Hindi site content brought back in line with the current site and schema; Tamil archived out of the live language switcher.

## [0.1.1] - 2026-04-16

Initial PyPI/npm release.
