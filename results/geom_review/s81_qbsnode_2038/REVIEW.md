# QBS node reconstruction pre-placement review

Viewed `node_outlines.png` for the exact generated current-plan LLfu/LLfd/NNfu kits (43.2 x 77.76 um). Verdict **PASS-COND for PLACE prototype after normal SYNTH/LEC gates**. No route or timing qualification is claimed.

The E input buses occupy separate lower/upper bands with the clock/reset pair at the intervening center. LLfu sends data north, LLfd south, and NNfu exchanges north/south, matching their inherited return-tree roles. The 196/196/202 exact plan contacts preserve their ordering and face assignments. The 66-bit horizontal data banks use 0.096-um M5 spacing; E contacts use M4 with ample vertical separation. No macro walls, channels, halos, notches or slivers exist because these are macro-free regular rectangles. The entire outline's maximum Manhattan span is 120.96 um, below 405 um; no extra relay cycle is required. Existing M5 PG stripe and E center clock/reset interfaces stay unchanged.

Conditions: actual placed density, pin-to-register locality, related-register reach, clock tap load and continuous PG must be inspected from the resulting ODB; this pin-outline picture establishes only the plan's geometric feasibility. The parent still needs three actual routed EQ receipts plus the remaining six child joins and parent timing. Nothing here substitutes stub headers for a qualified body.

SYNTH-only jobs use 8 GB/2 threads, with no PLACE or STA until this review and normal proof gates. GEN initial attempt failed solely from missing sparse `physical/common_flow/clock_family.tcl`; fresh gen2 after materializing the tracked directory passed all three. Original failed GEN retained.
