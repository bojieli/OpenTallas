# Disabled T51 ownership-constrained DATA model: FAIL retained

Personally viewed DATA_model/T51_owned_DATA_MODEL_LOOK.png. The single concrete model places all 9,288 proven exclusive DATA cells, preserving 9 shared cells, 447 reset/START infrastructure cells, all 52 other actual bands, 137,673 TAPs, all FF targets, source graph, masters, orientations, stages, cycles and public pins. Native phase/site/footprint allocation has zero conflicts.

The previous stranded DATA cut falls 2.240607 → 0.230819. A new local ring cut is 2.702951 at x60..70/y1137.5: ring FF drivers contribute 536.510 weighted crossings and owned DATA drivers 764.983, over 99.94% of demand. Full R2R stays 402.33um/0 over405; public pin max149.81um. This is an explicit capacity FAIL, with no native DB edits or physical stage release.

The separate feasible-region derivation selects no layout: 3,192 ring/stage0 movers have no empty fixed405/pin150 diamond in either T41 or T51; movable-to-movable405 edges stay coupled. Under T51 actual row/TAP/held-body authority, the common upper first-capture corridor allows146.88um horizontal spread, R0/MX same-width nonoverlap capacities2614/2629 against1013/1047 first captures. These are geometric capacity bounds, not a joint allocation or routing claim. T41 uses its actual mirrored pins/graph; no T51 rows/TAP inventory is claimed for T41.

Next: choose one coherent ring+stage0+owned DATA layout with companion area849.314um² for DATA beside approximately781um² ring FFs, and include current planned clock radius150um/load1500 constraints. Current source39 planning CENSUS records no violations (T41:78 taps/37480 planned sinks, T51:73 taps/35382). Planned counts are not actual FF or propagated-clock qualification. No clock/pin/reset contract adoption, GEN, PLACE, CTS, GRT, RC or STA. Original native GRT4843/fill/partial-face/source-clock qualification and95696 buffer-PG-null holds remain.

The pure classifier replacement preserves its original failed/terminated performance receipt. All264 literal patterns pass grammar and native positive/negative predicate equivalence; ownership policy and immutable inputs are unchanged.
