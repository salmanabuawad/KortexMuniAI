# Vehicle insurance extraction fix

Fixed the local deterministic vehicle-document extractor for Israeli insurance PDFs.

## Main fixes

- Prevented short/generic Hebrew words from being falsely detected as field labels.
- Fixed cross-page row grouping that mixed page 1 table fields with text from pages 2/3.
- Prioritized specific labels such as `שם בעל הפוליסה` over generic occurrences in policy prose.
- Corrected confidence calculation for normal label/value relations.
- Added strong insurer signatures so ordinary Hebrew words such as `כלל` are not mistaken for an insurer.
- Added `הפול` detection via strong document signatures (`pool.org.il` / המאגר הישראלי לביטוחי רכב).
- Added deterministic labelled extraction for mandatory-insurance start/end dates and premium.
- Kept vehicle-number candidate scoring deterministic and protected against ID-number confusion.
- Expanded real-PDF regression assertions.

## Verified on supplied PDF

Expected extraction now includes:

- vehicle_number: `7046676`
- policy_number: `201-502525667826-00`
- policy_holder: `אבו עואד נדא`
- id_number: `37005618`
- engine_capacity: `1197`
- production_year: `2012`
- insurance_start: `2026-08-02`
- insurance_end: `2026-08-15`
- premium: `234.00`
- insurer: `הפול`
- insurance_type: `COMPULSORY`

Vehicle extraction regression suite: 12 passed.

Frontend TypeScript compilation (`tsc -b`) also passes. A full Vite build could not be executed in the sandbox because the uploaded `node_modules` contains platform-specific Rollup optional dependencies from another OS.
