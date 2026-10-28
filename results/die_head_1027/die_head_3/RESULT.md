# DIE-HEAD-3 d150 event (2026-10-27, own runs, UNCHECKED unless NUMBER-CHECKed)
- Map: feed_map.py --dmax 150 on sfb250c landed_ocv + box_fix -> 304 regions (d150/map_d150.json). fallback_land plan: 358 crossings,
  188,808 ring bits, head pass +108 cyc (9,282+108 = 9,390 vs 10,357). Estimate: ESTIMATE.md.
- Compose (fallback_land compose --monitor region, base physical/die_plan/s81_head/die_plan.json): OK, types 16->22, 0 placement
  failures, landing_contract 0 errors (340 pins/1116 edges), boot <= 314 cyc; latency regen 327 lanes; event sha 457b6c2d667e,
  FB1 variant d6cbbe0fcb7c (intel2:/srv/opentallas-scratch2/claude/die-head-3/d150/event).
- G0C (check.py --completeness): PASS 0 E / 14 W, 22/22 types clean (d150/g0c_report.json; render die_plan.png viewed).
- Die GRT incl clock (die_trial kit FB1, spine_fishbone rep 250, site slide; 50 congestion it, -critical_nets_percentage 0; TT+FF):
  overflow 0 on all layers, 0 GRT-0113/4 (grt_TT/FF.txt). Clock tree.json and arr_TT/FF byte-identical to sfb250c (render viewed).
- Count-aligned margins (ca3.py, arrivals x1.05, K from derated lag, PROVISIONAL until MESO-COUNT-2): 358/358 D4, worst low 104.1
  (chW0_t__2), worst high 1255.0, K1 195 / K2 163 (lat 2/3 cyc).
- Die STA related pairs (main die_sta_related, g021 AOCV, shared droop by region, data droop class): 30 in-region pairs,
  zero-logic TT +392.4 / FF -234.6; HB4 plan TT +8.29 / FF +9.25 (54 k cells), abutted +35.0 / +3.4. Limiter: spine sp5->sp4 (budget
  model). Real views (results/die_head_1027/views, signed elemA/elemB clockfreeze capsules, 1320/1320 instances): 6/30 pairs real,
  real-only TT +310.66 / FF +130.23 before HB4 (sta_real/d150_sta_real.log). Hyb2 on real views TT -64.4 -> rejected.
- Lint with BLACKBOXED cores (lint/, Verilator 5.050, LAND-HEAD-BIND-1 gen2 landed top = OLD 427-row map, sources from
  claude/land-head-bind-1027, -DSYNTHESIS selects the (* blackbox *) elemA/elemB stubs + *_bb.v macros, -DOT_COLL_NATIVE32(_OFF)
  as LAND-HEAD-BIND-1 lint.sh): rc 0, 0 errors, 12.1 GB peak, 4:19 (vs OOM at 96 GB elaborated). Warnings pre-existing in
  cores/leaves: 13 MULTIDRIVEN (mesh_ep 6, coll_lane 4, host_ep 2, lep_nr 1), 27 UNDRIVEN (20 = bb stub outputs), 72 PINMISSING
  (66 ot_s81sl_slice_lep). Without -DSYNTHESIS: 7 errors (bb stubs lack INSTANCE param; ok_f2/ok_f3 need the NATIVE32 defines).
- gen phys --clock-landing hook: NOT started (needs LAND-HEAD-3 reserved sites + master_slice; landing_place.py/.tcl exist).

## 22:5x response to NUMBER-CHECK / COORD 22:31 (NC HEAD d150)
- STRUCTURAL HOLD FIX = region = partition (part map, regions_part.json): every one of the 427 plan ports is a count-aligned
  crossing, so there are NO in-region related pairs and NO HB4 (removes item (2) and the 6/30 real-endpoint issue of item (1)
  for related pairs). Own runs (UNCHECKED): compose --monitor region OK, 16 -> 16 types (no landed-mask split), 0 placement
  FAIL, landing_contract 0 E, boot <= 327; event sha 2a856db23fbb; G0C --completeness PASS 0E/6W 16/16 (render viewed); die GRT
  incl clock (FB1 sfb rep250, 50 it, cnp 0) TT+FF overflow 0 all layers, 0 GRT-0113/4, tree + arrivals byte-identical to
  sfb250c; CA (ca3 x1.05) 427/427 D4, low 104.1 (same 6 chW*_t__2), high 750.7; K1 252/K2 175; types with per-instance K 25.
  TOK +171 per head pass -> 9,453 vs 10,357 (DIE-HEAD-2/LAND-HEAD numbers, 3 cyc/crossing upper bound). Ring FF 0.323 mm2.
  Bind (bindrun.sh, claude/die-head-3-bind code): gen rtl --clock-landing rc 0, implemented, 427 crossings, 16 types, monitor
  region on all 16, 0 no-landed-input resets; d150 also binds (358 crossings, 22 types, 3 no-landed-input resets).
- (4) low side 104.1 = 6 mirrored chW*_t__2 (turnW*b -> tW*b10, d -129.1 x1.05) tree crossings: fix = one more count
  (start-tree PAD 1 on these 6 edges / K+1): low 937.4, high 1190.0, D4 kept, latency 2 -> 3 on those 6 only. Not applied:
  the PAD per edge is set in MESO-COUNT-2 count_align_plan.py (shared tool).
- (5) K=59: RTL K = K_eff - n0, n0 = origin_cycles(dst) - origin_cycles(src) of the start wavefront. The 12 K=59 crossings
  are the rib return channels chE/W*_r__0 from the rib-end regions (start-tree depth 23, origin_cycles 57) straight back to
  the start root F00: n0 = -57, K_eff 2 -> K = 59. It only re-aligns the two free-running counters (receiver started 57 cycles
  earlier); latency stays K_eff + 1 = 3. The ring keeps counts mod NT = 2^(log2(DEPTH)+1+LAPX) = 64 (DEPTH 4), so K=59 is the
  same reset value as K=-5: distinct RTL K values mod 64 = {-1,-2,4,-5}, 4 values (strap/type question unchanged).
- (3) die_sta_related --count-align does not exist on main yet (MESO-RECONCILE-1 rows pending); SS + start-skew row not run.
- (1) partition kits / glue views: not started; blocked on gen phys --clock-landing hook (rings + reserved sites) and the
  K-strap OWNER ruling (kits may be prepared, not enqueued).
