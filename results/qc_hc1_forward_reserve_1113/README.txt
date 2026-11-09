HC1W output-face forward reservation model, 2026-11-08 takeover

This is a model/contract only. No production source, RTL, pins or current HC0W A pilot was changed, and no HC1 physical pilot was launched. PIN CYCLES0. Original source/physical results remain preserved.

Actual observed HC1W north hotbin .877: 506cells,327 from u_bound.u_bout_cw_n1,167 output-port cells,2FSTART,10tap. Masters161DFFHQNx1,167INVx1,167BUFx2,1AND2x4,10tap. Read-only E6 OpenROAD unit414512-1794168252 exited0. Bound RTL uses ot_dp_st W516, cw_n1_is2_q/eq into cw_n1[515:0]/eq516. This is output-chain crowding, distinct from HC0 RSF and HC2 B_HW landing storage rings.

Captured existing PRE_GLOBAL_PLACE sites:517 cw_n1 N-face flops,46columns x19.44..116.64,14rows y1331.10..1334.61. Current face allocator uses40site column pitch2.16um and0.27um row height, reserving width for FF plus inverter/port buffer. A raw3-row stride would cross the existing typed writer-face:cw_n1 FSTART rectangle72.384,1330.56..81.024,1339.20; no blind stride implementation is offered.

The model reserves the entire FSTART rectangle BEFORE face allocation, then allocates disjoint2.16x0.81um family envelopes in the same columns at3-row stride. It skips30occupied family slots and places all517, minFFy1320.03, maximum additional old-site offset11.34um; reserved family envelope area904.5432um2. No family envelope overlaps another or FSTART; all remain inside the core. model.py reproduces candidate_sites.json and model.png. Floating calculations are rounded to1e-6um for overlap arithmetic only; input model coordinates are0.001um and no physical pin/audit tolerance is altered.

Production contract: the generator must emit the forward reservations from the SAME typed landing group rectangles used for actual landing placement, before the face allocator executes. Do not parse generated Tcl, substitute instance-name skips, or rely on helper definitions that execute later. Use actual OpenDB row/site/family dimensions; reject missing roles/unsupported faces/insufficient capacity. Preserve whole FSTART rectangles. A future source implementation must also account for live INV/buffer placement and any other typed groups intersecting the target band. This model does not establish detailed routability, final buffer containment or CTS membership.

Current pilot priority remains HC0W A with root-approved pending-reference watcher and fleet resource envelope; B and HC1 stay unlaunched. Canonical takeover lane: CODEX-QC-TYPES-REACH-1113.md.
