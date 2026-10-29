HEAD-START-3 (2026-10-29): step-5 START re-plan from ROUTED arrivals (plan hk4 = plan_spine_raw_rx_tx). Successor of
HEAD-START-2 (claude/head-start-2-1029@51730b6d7c). Run dir intel2:/srv/opentallas-scratch2/claude/head-start-3. No timing ECO.
Codex WIP tools (codex/head-kits-0251@735403ad0) were NOT re-run here (the vehicle was not rebuilt, see 3).

1. Routed clock proof (mk_proof_routed.py, CHECKED): the planner's own proof (codex-head-start-0251/input/proof, same keys and
   tree paths) with every number replaced by the HEAD-START-2 r1 routed readout (arr_{TT,FF}.txt, GRT50 RC): 11,176 nodes
   (rise N + fall M), 735 core taps (T/F), and NEW 1356 measured START clock taps '__st__<path>' (node -> local BUF8 -> FF CLK,
   max late / min early over the stage's FFs), which die_sta_related.virtual_tap then uses instead of node + median core-tap leg.
   Measured: routed node arrivals +0.29..+149.8 ps (median +40.8) TT vs the unloaded proof; START clock leg 16.2..103.0 ps TT
   (median 38.3) vs the 17.3 ps median leg the planner assumed.
2. Leaf re-plan (plan5.sh = codex final4.sh recipe + --start-prev leaf_plan4.json), three clock-cal forms in parallel:
   e  spice_edge (recipe):              EXACT FIXED POINT: 1707 stages, 0 parent/edge/offset/J/origin_cycles changes vs
                                         leaf_plan4; capture sites byte-identical; 1706/1706 clean, min sync dist 123.9 ps.
   k  inv tree spice_edge + BUF8 leg at the BUFx4/6f/24 envelope (component form, BUFx8 proxy UNCHECKED): 2 stages added,
                                         1 changed; 1708/1708 clean, min 119.9 ps.
   s  literal spice_cell: FAILS CLOSED (no BUFx8_ASAP7_75t_R row in SPICE_CLOCK_CAL_CELL). With a BUFx4/6f/24 proxy master set
      the whole-path bound puts ~+-5 % of ~1.4-2.8 ns on START taps only: 599 START edges unclean, stage set collapses ->
      not a usable gate form for mixed inv-tree + BUF-leaf paths.
3. Why the vehicle was not rebuilt: the re-plan reproduces the as-built edges/offsets exactly, so re-emit/map/pack would give the
   SAME netlist, and the routed STA already shows it fails: 513/1355 stage->stage crossings < 0 (HEAD-START-2 ca_check).
4. ROOT CAUSE (CHECKED, sta/): the START crossing model has NO data path. count_align_plan --start-tree clock prices a start port
   as clock-to-clock only (start_skew default (0,0)); the vehicle's START data path (launch CLK -> QN -> INVx1 -> BUF8 relay
   chain -> capture D, GRT RC, report_checks per endpoint, rerun reproduces r1 endpoint slacks byte-identically) is
      TT max 140.6..600.7 ps (median 304.7), FF min 91.6..420.1 ps (median 210.9); ~1.1 ps/um over the 360-um hop budget
      (median by hop: <100 um 177 / 100-200 214.9 / 200-300 289.1 / 300-360 369.7 ps).
   957/1355 crossings have dd_max > the plan's own start_skew_limit (sync_dist - 26.5); ALL 513 as-built failures are in that
   set. HEAD-START-2's diagnosis (routed clock +41 ps) is not the cause: on the routed proof the plan does not move at all.
   join_plan_vs_sta.txt: plan edge == built edge on every crossing (no emit/polarity bug); fails are fall->fall 399/1209 and
   fall->rise 113/129.
5. Measured-edge target (stage_k.py, CHECKED on the routed STA terms: TT setup x1.10/x1.05 droop + 60 unc, FF hold + 25 unc,
   NLDM, no spice/AOCV): one incoming crossing per stage (1 endpoint each), choosing the capture edge/J on the half-cycle grid
   per stage (realisable top-down on the tree): 0 < 0, min +90.11 ps, 22 < 100 (all 22 are hop 306-354 um, half-cycle
   quantisation bound: s+h ~ 595 ps window). 976 stages flip edge parity vs as built.
   START offsets: UNCHANGED vs head_start_1_1029 PLANNED (105..309) under the clock-only model; NOT promoted (they ignore the
   0.14-0.60 ns data delay, so per-stage J may move by a cycle). sim not re-run (nothing changed).
Next (two variants in parallel, 12.17(3)):
   V1 (model, needs ROOT-MERGE: shared tool): count_align_plan + die_sta_related opt-in per-port measured START data delay
      (interval shifted by [dd_min_FF, dd_max_TT] per start port from the routed vehicle, not the symmetric skew form), then
      re-emit / map / pack / rerun this vehicle -> expected = section 5 numbers.
   V2 (structure, existing flags only): smaller START hop (--start-max-hop-um ~200: dd median ~215 ps) + launch QN drive
      (INVx1 -> BUF chain is the slow element) so dd fits; still needs V1 to place the edge on dd.
   Gate needs a BUFx8 spice_cell row (MODEL-CORR) or the clock-entry master moved to a calibrated one (BUFx4/BUFx6f).
