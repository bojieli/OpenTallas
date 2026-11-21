# OPUS-FIX-KV-PV-R5 -> KV-PLAN-R5: D28 pv split rows and rules (draft 11-21 PST)

Proof type: kv3_pv_v3 -> kv3_pv_v3 (w = g0+g2) + kv3_pv_v3e (e = g1+g3), cut x 1080. Private tree epyc8
/srv/opentallas-scratch2/claude/opus-fix-kv-pv-r4/split28/tree5 (own copy), composer split28/compose12.py, plan por_split_12_composed.

## Form (all 15 pv types over/near cap: v1 v1n v2 v2n v3 v3n v4 v4n v5 v5n v6 v6n v7 v8 v12)
1. <v> keeps its name (w = g0+g2, T0Q*); <v>e = g1+g3 (T1Q*). Pairing verified on all 16 D27 binds.
2. core_moves: g1<->g2 column swap (pvg1_p* -> x 1131.84, pvg2_p* -> x 648.0, pv__u_g1_j / pv__u_g2_j joins), final-position overlap check.
3. Every window / ring core across x 1080 moves to one side (split28/straddle_1080.json, 1-4 per type). Moved windows keep >= 0.5 um
   from their neighbours (v3: L2289_0 -10.368 um, L2366_0 -7.776 um so L2393_0 / L2279_0 fit).
4. RING SAME HALF AS ITS BUS: each landing ring (cl_<bus>) sits in the piece that owns its bus window. v3: cl_i_vport_E_N_vo_d2
   (1088.64, 241.92) -> (967.68, 241.92) (w, N window 989-1039); cl_i_vport_E_N_vo (993.6 -> 976.32, 17.7 um channel to the cut).
5. START relay tx pin cland_rstart_out next to the cut (v3: (540, 756) -> (993.6, 756); hop to v3e rx < 100 um, else 545 um).
6. Each split needs a census (type_split census on the base bind_latency) and lane_reference (split_lane_reference_export.py on the
   base bind) in the spec, or the bind fails (R8_UNCOVERED / lane rows).
7. clock.reserved_sites_um and landing_reader_start / writer_start / raw_branches are dropped and re-derived by the split.
8. Tool: type_split needs main + claude/opus-fix-kv-pv-r5-tsplit (relay keys, collector_root_xy, wavefront_min_depth, column-swap
   core moves, base taps read before core_moves). Without the last fix any ring move fails 'clk_tN is not a tap of the base type'.
9. R8: re-derive once on the split bind (bind -> r8_refresh from its bus_groups -> rebind). Carry the pv_v5/v5n age_vport station
   (FABLE-PD-KV-0730 fix 5) in the same D28 pass so the table is refreshed once.
10. Reset: re-run RESET-RELAY-GEN-R3 two-pass bank_reset_delta (--local-taps, then --second-pass, reach 300) on each split piece's kit
    (pv_v3 / v3n / v7 were 290 / 282 / 269 um unsplit).

## Cost (v3, report.json)
- 39 cut ports / 39 lanes added (9,131 bits over 1,521 um, M4/M6 pairs); 9 lanes re-timed: L138 14->11, L1851 58->51, L1852 49->48,
  L1885 58->51, L1886 49->48, L2095 34->32, L2271 34->33, L2280 9->7, L2375 41->37 (fixed cycles moved onto the new cut lanes).
- Cells (G0 split 9/10): v3 275k place / 157k synth, v3e 269k / 155k.

## kv3_pv_v12 split rows (OPUS-FIX-KV-PV-R5 -> KV-PLAN-R6, 2026-11-21; COORD: v12 CELL-CAP 499,054 cells at D26 floorplan, no retry unsplit)
Schema: FLOW-STRIPBODY-1121 one schema, soft KV pv = plain cut (band = cut x 1080, one axis); same form as kv3_pv_v3 (proof type above).
Partition pv_N_7 (origin 4458.24, 13841.28, MX); outline 2160 x 1520.64 -> two 1080 x 1520.64 pieces.
1. Pieces: kv3_pv_v12 (w) = g0+g2 + u_efault|u_fch|vport_W*; kv3_pv_v12e (e) = g1+g3 + vport_E*. core_moves g1<->g2 column swap
   (pvg1_p0..3 648.0 -> 1131.84, pvg2_p0..3 1131.84 -> 648.0, pv__u_g1_j 708.48 <-> pv__u_g2_j 1244.16, same y/orient rule as v3).
2. Straddlers (split28/straddle_1080.json):
   a. ring core cl_i_pvw__u_TNQN_N_rN_b_d1 (1071.36, 164.16, 46.656 x 49.68) -> (1083.6, 164.16), piece e: its bus window
      i_pvw__u_TNQN_N_rN_b_d1 (S, local x 1141.1-1162.7) is in e (ring same half as its bus). Clear of pvg1_p* at x 1131.84 after the
      swap (gap 1.58 um; use 1082.16 for 3.0 um if the halo needs it).
   b. N windows: swap L2353_0 o_vport_W_N_vo_d4 (1065.16-1140.92, straddles) and L2249_0 o_vport_E_N_vo_d4 (989.18-1064.94):
      L2353_0 -> local 989.18-1064.94 (die 5447.42-5523.18, w = vport_W), L2249_0 -> local 1084.00-1159.76 (die 5542.24-5618.00,
      e = vport_E; 3.19 um to L1952_0 at 1162.95). Partner partition windows move with them.
3. R1 verilog_defines OT_PV_VPORT_SELREP32 on both pieces; R2 leaf rows follow their leaf (a "leaf u_vport_X" launch row whose from_um is
   on the other side starts at that leaf's anchor); census recomputed on the split contents (type_split census on the base bind) +
   lane_reference in the spec.
4. START relay cland_rstart_out next to the cut (as v3); clock reserved sites / landing starts re-derived by the split.
5. R3/R4/R5: r3_rows.py (epyc8 split28/r3_rows.py) on the split bind RTL for kv3_pv_v12,kv3_pv_v12e (vport lanes via leaf anchor,
   stations <= 300 um, u_bout rows; relay_sites of 3,197 vport bank flops per leaf at the anchor) -> leaf_first_hop 0/0 gate.
6. ONE r8_refresh on the split bind (bus_groups) -> rebind; tap rows for both halves from TAP-GRID-R4 after the bind.
Estimate: v3 floorplan ~490k -> halves 275k/269k place; v12 499k floorplan -> ~255-280k per half, under the 400k cap.
Tool: type_split = main + claude/opus-fix-kv-pv-r5-tsplit (epyc7 lane clone, 3a132dd5b5; base taps read before core_moves) — pushing after
my split bind is clean; FLOW-STRIPBODY-1121 also edits type_split.py (one commit owner rule: I rebase on theirs).
