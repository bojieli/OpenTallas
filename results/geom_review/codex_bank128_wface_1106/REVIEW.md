# Bank128 safe-form review — 2026-11-06

Images are drawn from generated kit macro-placement coordinates, exact current pin table, and the B ingress-guide rectangle. They are pre-build geometry reviews, not placed-logic or routed evidence.

Draft: `bank128_wface_plan.png` — FAIL geometry. The inherited X SRAM at y108.012 leaves only1.032um between its halo and upper W0 halo; lower channel is much wider. No candidate was routed from this draft.

Revision: `bank128_wface_revised.png` — PASS-COND for A/B physical trials. X moved to y96.252; both halo-clear channels are12.792um. Neither outline nor pins change. A and B now share the corrected geometry, M6 signal ceiling and single-root CTS; B adds the proved525bit write ingress and north-face guide. Actual config PLACE_DENSITY0.40, MAX_ROUTING_LAYERM6; no density tap OT_DTAP settings. Clock entry125.304,133.92 is outside macro halo, east of X. Existing power hooks retained; final routed PG/DRC remains to be measured.

N-face write bus terminates in the adjacent north register guide; stage-to-bottom SRAM span remains below~270um, within405um guidance. M6 supplies horizontal over-macro escape where M1-M4 SRAM obstructions forced M5 detours. Clear side channels and balanced horizontal corridors avoid the old near-touching macro wall. No pins move or face-order changes. Placement and post-CTS images must be inspected when available.

Conditions before adoption: parent must reserve the actual M6 hard-core obstruction/resource; sign-off and routed LEC must pass; WFACE+1 write programming/read-go guard must be composed by the native HC projection owner. No setup/hold/clock constraint was changed. This record authorizes diagnostic physical trials only.
