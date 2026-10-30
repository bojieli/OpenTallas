DIE-HEAD-34 lep_pair 777.6x492.48 variants VA / VB  (Thu Oct 29 07:32:40 PM PDT 2026)
WHY (CHECKED on the DIE-HEAD-33 V1 3_place, epyc2 die-head-33/lep/geom_v1/auto_geom.png viewed): all 55 SRAMs + logic sit in
x<450 and the right ~330 um is empty, because the V5 pin view (made for the 388.8 width) packs the 1114 S-face K pins
(M5 556 k_lo_*, M7 558 k_li_*/k_flt/k_rxv) into x 2.0..395.4; W face = 1026 coll pins y 2..465; clk/rst entry (388.92,246.24).
ESTIMATE (mk_variants.py, variants_report.json; CHECKED arithmetic):
  VA pins: same order per layer, uniform over x 2.04..775.0 on the existing track grid (M5 0.024+0.048k, M7 0.032+0.064k):
    pitch 1.392 um M5 / 1.344 um M7 (was 0.672-0.72 / 0.704-0.768); S-face track use 3.45 % M5 / 4.62 % M7 (about half of V1).
    Reach: K-lane logic can follow its pins east (the S face is local to every x); W coll logic unchanged.
  VB macros: 36 u_ep fifo/rb 256x64 SRAMs spread per row, new x = x + 4.32*round((x-155.52)*(F-1)/4.32), F 2.1362 (row span
    155.52..410.4 -> ..700); rows/orient/lattice residual kept; fifo bank6 d0 stepped 3 lattice steps left to keep the clk entry
    off macro+halo; legality: 0 overlaps incl 4.32 halos, max x 734.42 + halo <= core 773.28, clk not on macro (CHECKED).
    32x64 SRAMs (u_gb, u_ski near the W face) unchanged.
  fill_of_free: std area ~16.5k um2 vs free ~321k um2 -> ~0.05 at this outline in BOTH variants (V1 measured 0.0499) = rule
    FAIL (>=0.15) stays reported, not waived. Fill >=0.15 needs free <= ~110k um2 (about the old 388.8x432 outline).
  Not in VA/VB: the Codex DPL long-capture fix (codex/head-lep-serdes-1847, post-place) - apply to the winner if r2r > 405.
  Parent: the pin view is a lep_pair pins_file delta (the parent lep0N plan reads the same file) -> G0C on adoption.
KITS: lep_pair_kit_777v.py (= DIE-HEAD-33 driver + OT_LEP_PINS/OT_LEP_CHILD env), src plan intel2 die-head-32/src25m
  (a7435da4), tools main e4b3808d5. Kit diff vs V1 kit: io.tcl/pins.json/plan_pins.json (+ macro_placement.tcl /
  macro_grid_snap.json in VB) + pinreg_measure.tcl (main 62d8d8746) + provenance/freeze; RTL identical -> LEC = the V1
  parallel LEC 2876937 on the same RTL (lec.py renamed lec.py.parallel, as V1). Pre-floorplan gates run fail-closed in run_kit_hbm.sh.
RUNS (epyc2 /srv/opentallas-scratch2/claude/die-head-34/lep/{va,vb}/kit/ot_s81hd_lep_pair_kit, ot-run from intel2,
  run_kit_hbm.sh place 32 16): VA unit oth-ubuntu-3836197 (intel2 die-head-34/lep/va_place.otrun.log),
  VB unit oth-ubuntu-3836194 (vb_place.otrun.log). AUTO-GEOM watchers epyc2 die-head-34/lep/geom_after_{va,vb}.sh ->
  geom_{va,vb}/auto_geom.{json,png} (GRT M7, 50 it); they wait for 3_place.odb only (a failed run leaves them waiting).
