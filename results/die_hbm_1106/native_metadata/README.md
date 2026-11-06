# HBM native metadata repair

This event repairs existing generation metadata while retaining all422active lane records, every hard-core record and every internal-station record exactly. Canonical JSON hashes are in identity_proof.json. Core connections, clock entries and macro records remain byte-identical to the current main base. WBQ safe-split activation is separate and absent here.

Twenty intentional disjoint same-face turnarounds are explicitly annotated; ordinary reach, station and pin checks remain. Six missing root buses exactly match the actual t11m79f native root port widths/directions and restore immutable r5_NE windows. Existing live FT geometry is unchanged. The full source-aware schema check passes with0errors. No geometry render is necessary because there is no moved or resized geometry.

The retained ledger contains every removed record:4orphanports,30unused FTslots,33unreferencedregularbuses,1obsolete latencygroup.23unique endpoint order fields are repaired while shared hard-type pin order remains fixed. The existing1980bit L12m_word leg is now named L5037; its1016bit L12ms leg remains. Active lane payloads and all station cycles are unchanged.

These checks qualify a metadata repair. They do not establish full parent timing, token scheduling or functional assembly readiness.
