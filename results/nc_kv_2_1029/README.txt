NUMBER-CHECK-KV-2 (2026-10-29, Claude). Independent recompute of DIE-KV-27/28 die STA + reach headline numbers.
Inputs: intel1 die-kv-27-1029/{edges/arr_*.txt (raw OpenSTA readout), proofE/tap_arrivals_*.json, proofE/droop_regions.json},
die-kv-26-1029/plan_e26a.json, codex-kv-25-1029/native6/native_bind.json, 4 signed core views kv3_head_eighth_e{1,2,5,6}@3e7fccd216,
die-kv-28-1029/prov/{plan_e27f_prov.json,boundary_edges_e27f.json}, intel2 codex-provider-import-1029/proposal_kv6/placements.json.
Own code nckv2.py (no die_sta_related import; own CPPR/LCA, interval, wander, lag margins, start-port sync distance, own AOCV
from clk_aocv_table_g021.json, own ETM parse, own pair sets, own 12.19 labels). Published inputs taken as given: spice_edge INV
factors 0.9324/1.0241 TT, 0.938/1.0487 FF; AOCV table; plan geometry via schema.Plan.to_die. Run dir intel1:/srv/opentallas-scratch2/claude/nc-kv-2-1029.

Results (mine vs reported):
 raw identity: 1920 taps x T/F rows == proof taps (0 mismatch); all node arrivals present in raw N/M rows.
 OpenSTA by hand (spot_*.tcl, same combo.v + die_<C>.sdf): 13 tap ports x 2 corners x {rise late/early, fall late/early}
   = 104 values, max |OpenSTA - proof| 0.000 ps (incl. worst-pair taps hg_WS_7 t3/t8, pv_S_1 t10/t12/clk, pc_WS_7 t6, phy_WS_7,
   CA worst pc_ES_3/pc_ES_4, hg_EN_1, hgi_EN_2). Register clk->Q own OpenSTA (1 DFF, 6.6/0.6 fF): TT 77.92/46.00 FF 54.64/32.27
   vs regchar 77.75/45.16, 54.70/32.01 (<=0.84 ps).
 CA: 3595 crossings, 0 unbound, 0 no-taps; worst lo TT 104.806 / FF 109.642 (ties: L575_3=L1113_0 pc_ES_3->pc_ES_4,
   L381_0=L2235_2 hg_EN_1->pc_EN_1); worst hi 515.895 / 516.298; 0 <100; guard 0 fail.  CONFIRMED 104.8/109.6.
   PHY crossings (BUFx24 tap pads) min margin TT 309.6 / FF 328.8 -> spice_edge vs BUFx24 spice_cell choice cannot flip them.
 START: 1687 rows (1570 fall-edge), 0 fail; clk->Q 45.162..77.746 TT / 32.012..54.695 FF vs min limit 92.4 (0 rows limit < clk->Q).
   NOTE: the "77.7 / 54.7" is the declared register clk->Q (start wire mismatch 0, source model-coroute), NOT a measured skew;
   the start-port gate is the STA sync distance: worst 115.18 TT (fall) / 150.93 FF vs 26.5 aperture.  CONFIRMED (with label).
 intra TT setup 314.300 (hg_WS_7 t3 e1 -> t8 e6), seam TT setup 554.119 (pc_WS_7 t6 -> phy_WS_7).  CONFIRMED.
 real-view FF hold -50.980 (hg_WS_7 t8 e6 core launch -> t3 budget glue capture), 3083 neg / 13440 real pairs; TT -28.089.
   Hand: ea 1908.92 + e6 out_min 283.51 - (lc 2024.16 + 202.5 + 9.891) - 25 + CPPR 50.63 - AOCV hold 32.50 = -50.99. CONFIRMED.
 12.19 classification: every tap carries the declared budget register (0 kits) -> 28970/28970 intra, 768/768 seam unmeasured
   -> BLOCKED(kits) CONFIRMED.  Type count: 54 intra + 8 seam = 56 partition types without a view (kv3_phy/_v1 seam-only,
   single-tap); "55" DISAGREE (should be 56; tool record lists 54 + 8).
 START reach (plan_e27f_prov provider): 1772 edges, max far-corner Manhattan 367.47 um, 0 >405.  CONFIRMED.
 Boundary 331 edges (87 start_in, 87 reset_in, 157 start_out) vs proposal_kv6 placed cells: max over ALL stage cells 355.832
   (hub_Ei/hub_Eo -> b4601/b4643), out edges max 320.94 (all cells; reported launch FF 317.76), 0 >405.  CONFIRMED.
   (plan stage rects instead of placed cells: 359.61, still 0 >405.)
 Sensitivity (INFO, existing runs): DIE-KV-28 sta_E_cell (spice_cell with CKINVDCx16 factors 0.9483/1.0269) gives CA TT lo 58.6
   FAIL (90 <100); the gate number holds only under spice_edge INV (COORD 10-29 rule for inverter trees).
Limits: views matched by whole-file pins sha (e6 168/256 vs tool canonical 256; worst values identical); GRT basis.
