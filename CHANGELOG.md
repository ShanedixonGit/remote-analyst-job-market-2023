# Changelog

## [Unreleased]

### Added
- Data-quality check 7 counts near-duplicate postings and how many disagree on extracted skills, so the README's near-duplicate figures can be reproduced from a query.

### Fixed
- README said SQL appears "more than twice" as often as any other skill; it is about 1.5 times as often as Excel.
- README said 101 rows were removed at load; 102 were (101 duplicates and one empty row with no company).
- README said "collectedtoday" and gave no collection date for the live sample.
- Chart 03 title said four skills appear in "at least a third" of postings; Tableau is at 32.5%, so it now says "at least 30%", the threshold the chart actually uses.
- Chart 06 no longer says the live sample was "collected today", and reads the 2023 sample size from the data instead of a hardcoded 11,496.

### Changed
- README restructured into Part 1 (the 2023 market, from the course dataset) and Part 2 (the current market), with a data model diagram, a repository layout, and the gaps the Part 2 data model has to close.
- README no longer embeds a 274 KB base64 image that GitHub does not render; the CRISP-DM diagram is now Mermaid.
- README links to the SQL files are real links again instead of code-formatted text.
- Reproduce steps use uv.
- `build_database.py` now prints how many source rows were removed as duplicates and how many were dropped for having no company, so the 785,741 to 785,639 row count can be traced.
