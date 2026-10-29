# DIE-HEAD-18 (2026-10-28): built ring clocks in the HEAD CA gate (opt-in --ca-ring)

Tool: die_sta_related.ca_ring_fn + --ca-ring SPEC (gate) / count_align_plan --sta-ca-ring (planner, same function).
A count-aligned ring writes on the forwarded clock and reads on the local clock:
writer = launch tap + fwd_out(src type) + fwd_wire + fclk_in(dst type); reader = capture tap + reader(dst type).
Default (no spec) is byte-identical. Pairs whose types have no measured data keep the declared common latency (label "declared").

Spec ca_ring_hd_tile.json (CHECKED own, routed DH17 hd_tile, GRT RC SPEF):
| ps | fwd_out (clk->fclk_out_o) | fclk_in (fclk_in_i->2298 writers) | reader (clk->628 ring readers) |
|---|---|---|---|
| TT | 192.6-196.7 | 189.4-212.7 | 501.4-539.8 |
| FF | 157.6-161.2 | 155.9-176.9 | 401.5-435.6 |
fwd wire: abutted tile pins (706.3 -> 708.48+2.1 um), 4.3 um, bound [0,1] ps.
Legacy chain: clk -> h15_rs BUFx24 -> wire17444/3/2 -> output655 BUFx2 -> fclk_out_o (fwd_TT.txt).
Shift on a tile->tile pair: TT lo +92.0 / hi +157.8 (the lag grows: writer clock ~400 vs reader ~520).

Gate (shared model, clock_variation table, inv2, spice, CPPR LCA, shared droop; st_max_2 stages; DH17 clk17_max_2 inputs):
- r0 no ring: CA 427 TT 136.0/574.9, FF 163.8/626.0 PASS (repro of DH17 / NUMBER-CHECK-HEAD-1).
- r1 --ca-ring (gate): built 240 ports (hd_tile->hd_tile) worst lo/hi TT 602.0/1134.6, FF 563.1/1166.0;
  declared 187 ports TT 136.0/574.9, FF 163.8/626.0. PASS.
- r2 planner + gate ring: same plan (worst 136.1/573.7; the gate worst rows are declared ports).
Declared 187: 139 non-tile<->non-tile, 24 X->hd_tile (src fwd_out unknown), 24 hd_tile->Y (dst ring unknown).
Sensitivity (INFO, not a gate): unknown sides bounded to [0, common latency] give TT lo -91.1 / -239.4, so the
other partition types need measured ring clocks (turn/spn/ctl/... kits) before HEAD freeze.

--start-prev (fg2-ststable @2a972d7368) on the real HEAD plan: re-plan of pass-2 inputs with prev = pass-2 plan:
prev_kept 357/683, emitted 358 stages = st_max_2 = st_max_3 (0 diffs, the fixed point stays put); gate unchanged.
From pass-1 inputs with prev = pass-0 plan: 12 diffs vs st_max_1, all EDGE_FALL rise->fall (+1 flop), result = st_max_2
(not tie flips; prev is kept only where still clean).
