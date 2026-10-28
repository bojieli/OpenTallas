# DIE-QC-10 (QC die owner): QC local-form plan event, trial8 = rt2 ladder-arm forwarding tree + fork start ports

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc10-1028 (est/, plan/, trial8 kit, c8_TT/FF clock-only GRT, ca/t8).
Plan inputs (read-only): codex-die-qc-0359-1028/build_inputs (K2b event qc_k2b_phase12.json, part_region, regions_map, feed_grpP).
Tools: claude/die-qc9-1028@6e978b3184 (die_trial with the DME snake + plain-stage fallback; RM129). No tool change on this branch;
the scripts here are lane-local estimate/recheck wrappers.
Labels: CHECKED = computed by me from the named files; UNCHECKED = model or not independently rechecked; INFO = never a gate number.

## 0. Collected (DIE-QC-9 live job)
- ca/t6/sta_none (INFO bind, plan-FAIL dropped): intra TT setup +291.4 / FF hold -308.9; landed CA worst lo 104.4 / hi 108.1 TT,
  start-skew 16/312 TT, 5/312 FF; 59 region pairs unbound (CHECKED from the log, INFO only). sta_HB4 CRASHED in main
  die_sta_related.intra_bits: `json.loads(...).get("pins")` on a list-shaped pin file (AttributeError). Main bug in the HB4 bit census
  on the K2b signed-SU pin views; not rerun (INFO run, superseded by the local form).

## 1. Plan inputs (CLK-LOCAL-EST-1 + COORD 07:52 ruling)
- Data-link graph (CHECKED): 2537 crossings, 857 directed / 555 undirected region pairs, ALL between touching regions.
- feed_grpP (current) is already a forwarded tree: 312 edges, all data pairs, depth 21. 96 of its edges have data only child->parent.
- Per column the data form is: slice hub (10 regions) + two A0 arms of 2 x 4 regions (x0 / x1 columns). Each arm is a ladder:
  x0 and x1 vertical chains plus rungs on every row; the slice enters the arm at both the x0 and the x1 top regions.
  feed_grpP threads each arm as ONE 8-region snake (su_l1 -> bn_00 -> bn_01 -> bf_00 -> bf_01 -> bf_11 -> bf_10 -> bn_11 -> bn_10), so
  the slice -> bn_10 / st_b,hc2 -> tn_10 links and the arm rungs close 5-10-hop loops (the 125 crossings >4 hops; CLK-LOCAL "137").
- RE-TREE rt2 (plan/feed_rt2.json, mk_feed_rt2.py): x0 chain from the slice (su_l1 / st_a), every x1 region hangs from its SAME-ROW x0
  neighbour (rung). 72 regions re-parented; slice hubs, slice chain and coll band unchanged. Tree depth 21 -> 19.
  - Every arm link then closes a <= 4-hop loop. The only residual long loop is the coll_s ring (coll_s <-> c_W5_bf_00 vs the coll
    chain f0..f4 -> sl_W5_stm): a ring of 14 regions, so any tree leaves one 13-hop edge. The cut stays on coll_s<->c_W5_bf_00, the
    fewest-crossing edge (5 serdes crossings; cutting at coll_s<->coll_f0 gives 6).
- Start/count (12.16b(iv)): start tree = the clock-forwarding tree with a START-TREE-1 fork start port per edge (launch and sync flop
  on the two legs of the fork node). Modeled here as a d = 0 +- 40 ps leg row with the main clk_aocv OCV (no region-union hull);
  the real port comes from START-TREE-1. Reset release rides the same ports. Restoring stage every ~5 hops is NOT in trial8 (DCD
  check owed, COORD (4)).
- Alternative also estimated (est_spine.py): column spine through each arm + slice-chain trunk with a start pipeline beside it:
  2862/2862 at D4, 0 fail, 0 ambiguity (ESTIMATE). Same outcome as rt2; rt2 kept because it is the ruled tree form and builds on
  die_trial link feeds unchanged.

## 2. ESTIMATE before build (est_feed.py; model constants calibrated on trial6, UNCHECKED)
- Region tree: leaf arrival = tap + (-104 + 0.498 ps/um x far Manhattan) TT (-89 + 0.417 FF), fit on 735 trial6 feed edges (resid sd 171).
- Spine/feed wire 0.281 ps/um TT (x0.837 FF). OCV: main clk_aocv table g021 on both unshared branches + core latency 250/202.5,
  droop not shared, + in-region spread (c_* 150 gate bound, su_c 92.4, others 41), +80 ps width (validate.py: model med 344 vs
  measured hull med 420).
| tree (start = fixed clock tree, fork ports) | data loops >4 hops | D4 | D8 | FAIL | min margin lo / hi |
|---|---|---|---|---|---|
| feed_grpP | 125 | 2777 | 72 | 0 | 104.4 / 147.7 |
| rt1 (two chains per arm) | 125 | 2849 | 0 | 0 | 104.4 / 499.0 |
| **rt2 (ladder arms)** | **5** | **2849** | **0** | **0** | **104.4 / 686.7** |
| rt2, slow spine 0.40 ps/um, region x1.3, c spread 180.7, scale 1.05 | 5 | 2843 | 6 | 0 | 125.5 / 269.1 |
(2849 = 2537 data + 312 start rows.) Without fork ports (planner's own min-ambiguity tree) the same rows give up to 8 cycles of
path ambiguity and 78 FAIL: the fork start port is the load-bearing part, as CLK-LOCAL found.

## 3. BUILT trial8 (rt2 feed, trial7c in-region form: c_*/su_c DME, su_c snake + tap-leg pricing, early hang 1.548/1.293)
- Kit: 29,112 clock cells (trial7c 29,659), 0 illegal, body bays 0 pads, 312 feed edges / 541 mm feed wire (CHECKED kit8.log).
- Clock-only GRT 2W2S, TT and FF: EXIT 0, overflow 0 on all layers, M8 0.36 % / M9 0.51 %, wire 5.689 m (CHECKED clock.log).
- Renders viewed (trial8_plan_die.png, _E2arms.png, W5coll): each arm shows the x0 spine with a rung on every row; slice chain on
  y~12.5 mm; coll band on the W edge. PASS-COND: one c_W5_bf_01 feed detours ~1 mm west via x~750 um near coll_s (inspect at the
  plan-event GEOM review).
- In-region spread (eval8.py, tap late + declared core insertion; OCV term 0.062 x entry->tap UNCHECKED), TT med/max:
  su_c 56.5/92.4, 0/12 regions >150; sl 13.1/36.3; c_* 73.5/180.7, 34 TT / 12 FF regions >150 incl. OCV-est (unchanged: waits for the
  A0 centre entry + parent trunk, section 5).
- CA on BUILT arrivals (runCA8.sh: lpo -> ca_spice x1.0485/x1.0552 -> proof -> + fork start rows -> count_align_plan with the
  CA-OCV-1 hull: --sta-clock-ocv table, shared droop, cppr-lca, spice; start tree fixed to rt2 via cap_fixed_tree.py):
  - **2849/2849 at DEPTH 4, 0 FAIL, 0 path ambiguity, 312/312 start edges clean, worst margin lo 105.0 / hi 412.2 (TT u FF),
    MC 500 chips 0 violations (worst 105.1 / 415.0 to guard)**. UNCHECKED-independent (needs NUMBER-CHECK); start rows modeled.
  - By loop length (TT unshared med/max, min margin): 1 hop 1782 x 1.31/2.90 ns 109.1; 2 hops 314 x 1.83/2.47 ns 109.6;
    3 hops 396 x 3.07/3.51 ns 105.0; 4 hops 40 x 3.21/3.52 ns 377.0; 13 hops 5 x 7.78 ns 412.2.
  - RESIDUAL direct long-loop crossings (COORD condition): 5 (coll_s__serdes_tx_tx_flit_2__0, coll_s__serdes_tx_valid_tx_v_2__0,
    io_serdes_2__rx_flit_serdes_rx__2, io_serdes_2__rx_v_serdes_rx_valid__2, io_serdes_2__tx_up_serdes_up__2), 7.78 ns unshared,
    D4 (not D8 even), margin >= 412 ps on the built bound. Was 125 (>4 hops) on feed_grpP.
  - INFO, same arrivals with the planner's own start tree and no fork ports: 8 FAIL (c_W1/E3_tf_00<->01, 6 ambiguous cycles).
- Not done here: count_align_bind + die STA (related pairs, start-skew rows) on the trial8 bind; they need the START-TREE-1 port form
  in the bind.

## 4. A0 parent LOCAL trunk (COORD 07:5x: DIE-QC-10 owns it) - ESTIMATE / plan spec, nothing built
- Measured default CTS (QC-A0-KITS-3): NK 619/508, NL 606/495 TT/FF, parent-reg skew 170-225 TT.
- Plan form: centre entry (228.97, 578.88) on M5 -> plan-built balanced trunk (DME, delay mode, tap legs priced in ps as in su_c) to
  the 18-19 child clock pins and to ~16 glue-register leaf clusters (each <= 200 um, plain local tree); child insertion folded in
  as early-hang offsets (node 222.3, romleaf 170.3, rawleaf 158.0 TT child CTS).
- Estimate: farthest child pin 641.6 um x 0.435 ps/um (0.281 x QC measured/model 1.548) = 279 ps trunk; node flops 279 + 222 = ~500 TT;
  romleaf/rawleaf/glue hang late to match -> target ~500 TT / ~420 FF (x0.835), spread target <= 60 ps (DME model 2-6 ps on su_c).
  That is ~120-170 ps below default CTS and removes the 170-225 ps parent-reg skew. The die region tree then taps the A0 centre pin
  EARLY by ~250 TT (12.8 v5.0 early tap, as CORELAT for SU), which is the c_* centre-entry plan delta.
- Cells: trunk + leaf trees ~ few k << 400k. Next: parent kit CTS with the plan trunk (OT clock from a planned tree.tcl, not
  TritonCTS), on the Codex child fixtures, then real insertion -> c_* region DME -> recheck c_* spread.

## 5. Next (DIE-QC-11)
1. Plan event K2b-L: feed_rt2 + START-TREE-1 fork ports (shared lane) + restoring stage every ~5 hops (DCD spice check) ->
   G0C -> kit -> clock GRT0 -> bind -> die STA (related pairs, start-skew) -> NUMBER-CHECK.
2. A0 parent plan trunk kit (section 4) -> A0 centre-entry delta for the 192 c_* regions (34 TT/12 FF >150 today).
3. GEOM review of the c_W5_bf_01 feed detour; HB4 intra_bits list-shaped pins crash -> FLOW owner.
