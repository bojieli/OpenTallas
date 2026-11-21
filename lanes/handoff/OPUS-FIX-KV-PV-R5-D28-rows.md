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
