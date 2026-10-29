DIE-HEAD-30 2026-10-29 (HEAD die owner). hk5l = fix-only plan delta on the frozen hk5 plan (COORD 11:09: pins not moved
with the hk5 windows = FIX, allowed on the frozen plan). Results only.

INPUT  Codex SOURCE7 source plan intel2:/srv/opentallas-scratch2/claude/codex-head-0830/tile_source/source7/source_plan.json
       (sha256 5d37fc9f..., = the plan of the gen4 hd_tile kit and of the die-head-29 V1/V2 variants; hk5 i/o windows).
SCRIPT hk5_land_pins.py (deterministic, asserts old geometry). OUTPUT source_plan_hk5l.json.gz (sha256 6be9e31d...). move.log.
WHAT   DIE-HEAD-26 hk5_tile moved the hd_tile i/o data windows 354.24-654.272 -> 708.48-1008.512 (+ tile-facing windows of
       turn_a / turn_b / 4 spine shims), but clock_landing_plan.py had derived the count-aligned landing scalars from the
       hk4 bus point: fclk_in/out, cland_fstart_in/out, cland_dn/up_ready/fault, their edge_clocks taps and the ring
       storage bands stayed at y ~504 (GEOM-59 11:12: pin -> farthest ring slot max 339.1 um FAIL).
       Moved +354.24 on the same faces / frame offsets as hk5_tile: hd_tile 8 scalars + fclk_in_i edge tap + ring band;
       hd_turn_a 4 + tap + band; hd_turn_b 4 tile-side outputs; eshim_tx 4, eshim_rx 6 + tap + band, wshim_tx 4,
       wshim_rx 6 + tap + band. hd_tile ring band [17.28,706.32,116.64,788.4] (99x82 W-corner block) ->
       [17.28,708.48,47.52,1008.512] = a 30.24-um W-face column along the i pins (same column form as turn_a/shims,
       spread 4521.6 um2 reserve / 9072 um2 = 2.0). 0 cycles, no RTL change (gen5 kit rtl/ byte-identical to gen4).
G0C    check.py --completeness --landing source_sidecar.json: base 3842 ERROR / hk5l 3842 ERROR, error message sets
       IDENTICAL (0 new, 0 gone; CHECKED). The 3842 are pre-existing on SOURCE7 itself (3515 clock_landings
       'rst_start_raw_* infrastructure pin used N times' from the Codex private raw-START exports + 327 latency table
       rows) -> SOURCE7 G0C is not clean on its own: Codex/HEAD-START item, not this delta.
       Abutment of the moved scalars is consistent by construction (tile E out y = tile W in y = shim/turn tile side).
KIT    gen5 = codex head_tile_source7_kit.py on the hk5l source (intel2 die-head-30/hk5l/gen5, rc 0). Diff vs gen4: io.tcl
       (7 landing pins + fclk_in_i), landing_placement.tcl (ring rect), landing_contract.json, plan_pins.json, freeze.json.
       PLACE launched as the two 12.17(3) variants on top of the pin delta (same kit patches as die-head-29 V1/V2):
       var_v1 = xvo_q in the xo bank + PLACE_DENSITY .35 (unit oth-ubuntu-4032276), var_v2 = xvo_q + 40 % channel
       blockage (unit oth-ubuntu-4032264), started 11:38, GPL ~70-80 min.
CLOCK ENTRY ESTIMATE (clk_entry_est.py on the die-head-29 trial geom.tsv, 28,075 clocked flops; CHECKED own run):
       one entry anywhere cannot meet 12.8b reach ~200: (354.24,354.24) max 1003.2; (354,717) max 1012.4 (p50 268.7);
       centre (354,518) max 839.0. Greedy cover on a 17.28 lattice needs 16 entries for <=200 (reach 199.3) or 12 for
       <=220 (219.6). => the predecessor's 'move the tap to (354,717)' does NOT fix clock_reach; the structural fix is a
       pre-placed local entry set (12-16 FIRM clock cells = in-tile islands, 12.8b) fed from the one die tap -> needs the
       kit's local clock tree to pre-place them (plan-computed sites); proposed, not built.
