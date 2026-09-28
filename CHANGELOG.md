# Changelog

## [Unreleased]

### Fixed
- Chart 03 title said four skills appear in "at least a third" of postings; Tableau is at 32.5%, so it now says "at least 30%", the threshold the chart actually uses.
- Chart 06 no longer says the live sample was "collected today", and reads the 2023 sample size from the data instead of a hardcoded 11,496.

### Changed
- `build_database.py` now prints how many source rows were removed as duplicates and how many were dropped for having no company, so the 785,741 to 785,639 row count can be traced.
