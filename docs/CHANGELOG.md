# Changelog

All notable changes to IMDb are documented in this file.

## Unreleased

### Added

- Moved supporting project documentation into the `docs/` directory.

### Changed

- Updated the contribution agreement.
- Normalised Black configuration, README badge references, and README badges.
- Standardised GitHub support files and `.gitignore` entries.
- Applied Black formatting.
- Ignored the local `Documents/` directory.

### Fixed

- Hardened IMDb lookup safeguards.
- Fixed IMDb lint and mypy checks.

## v2.0.0 - 2026-04-28

### Added

- Released version `2.0.0`.
- Added OMDb-backed title search details and README troubleshooting notes.
- Added PEP 621 package metadata.
- Added GitHub Actions testing, Black linting, CodeQL, and README badges.

### Changed

- Hardened IMDb lookup handling.
- Replaced stale browser user-agent headers.
- Updated README plugin details and formatting.
- Standardised CI workflows and Black lint checks.
- Ignored Supybot runtime directories and Python cache artefacts.

### Fixed

- Restored title search behaviour and fallback handling.
