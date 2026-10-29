# HEAD START physical forest prototype review

Picture: `results/geom_review/head_start_leaf_1356.png` (personally viewed).

The 351 count origins follow the existing 327 physical clock groups. Intermediate START stages follow the clock-forwarding corridors. The spine detail shows local leaves at the five actual partition capture sites instead of a 2.4 mm partition star. Existing raw-reset relays feed nearby stages; the drawing has no die-reset star. Hard-core bodies remain outside the shown START-stage sites. The actual raw reset source census covers all 1356 stages within 321.323 um. Existing data buses, 24 unlanded spine links, physical clock groups and PG topology are unchanged.

Verdict: **PASS-COND for the physical prototype**, with the actual mapped-cell packing review required before GRT. This drawing covers planned stage sites rather than only the flip-flop footprints: the physical prototype must include all mapped combinational cells too. Parent has separately measured 14680 actual cells/5299 flops, full-body parent reach 365.175 um and raw-source reach 328.073 um, but those values require its own actual packing review. The joint START/clock/PG route, real partition views, related STA and reset phase qualification remain open. This is not a freeze or G4 review.

Prototype bootstrap price: SETTLE 74 versus the former 64, +10 boot cycles and zero steady-state data cycles. The four-cycle local-reset guard is a prototype hypothesis pending built clock/reset timing; actual production START offsets remain unqualified.
