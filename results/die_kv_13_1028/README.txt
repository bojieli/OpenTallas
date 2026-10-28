DIE-KV-13 2026-10-28 (KV die owner; successor of DIE-KV-12 1408708b80, COORD 6c0fa2f33 / 09:38 batch).
Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-13-1028.  Worktree intel1:/srv/opentallas-scratch2/claude/wt/die-kv-6.
Main at start 6a750743dc (QC-11 1465eff51c, KV-12, FLOW-GEN-1 NOT merged; FLOW-ONEMODEL-1 started 09:32).
CHECKED-own = my tool run reproduced/measured; nothing NUMBER-CHECKed independently.

(1) INVERTER-TREE SOURCE EVENT (kv13_event.py; worktree tools, no fork)
  a. In-process reproduction of the DIE-KV-12 inv r150 phase bind (same argv as its ca.sh): 3595/3595 ports equal
     (K, depth, sched_lat), rc 0  [CHECKED].
  b. ECTL K round trip per frame (Codex analyse_ectl_ca member selection on bind_s2 bus_groups; landed-stage model
     landed = sum(sched_lat over the lane) + lane constant, which reproduces RT20 on bind_s2 32/32 [CHECKED]):
     on the inverter K: RT 17 x8 / 18 x17 / 19 x4 / 20 x3 -> the "K round trips differ per frame" bind error returns.
     Equalised to 20 by the Codex ectl_ca_candidate rule (extra cycles on one non-tree request crossing into the ectl
     sink, depth re-derived): 29 rows, +62 crossing cycles (Codex RT20 on the BUF table: 31 rows +106).
     Re-bind verify: 0 identity/loop errors, 500 samples 0 window violations, min 106.5 / 118.1 ps; model RT 20 x32.
  c. Gate (main die_sta_related on ev1/bind.json, region key, HB4, OCV table, spice, cppr-lca, shared droop):
     CA TT 0 fail (min 105.2), FF 1 fail (L678_0 87.0 = the DIE-KV-12 phy-column class, FLOW-ONEMODEL-1 bug 1),
     start-skew 0/189 TT and FF  (= DIE-KV-12; the ECTL extras cost no margin)  [CHECKED]
  d. COMPOSE FAILS (shared tool gap, not KV-local): clock_landing_plan.compose -> count_align_bind.strap_ties
     KeyError 'start:hg_EN_1->hg_EN_0': strap_ties/compose do not know START-TREE-1 start ports (a region's tree_port
     is a virtual start port, not a landed data bus).  This is the DIE-HEAD-11 "compose/clock_landings start pins" slice
     (COORD 09:38 (2)).  So no strict bind / R8 regen / pads / image / token sim on the inverter event yet.
     Ready for it: recipe_kv13.json (recipe_kv8 + clock_landing_table -> results/die_kv_13_1028/event), run_bind13.sh,
     r8_13.sh (DIE-KV-8 R8 regen recipe), ev1_bind.json.gz (the equalised count-align bind).

(2) STEP-5 ESTIMATE (12.14b, UNCHECKED-indep; est/):
  VPORT RT (DIE-KV-11 vport_rt_est.py, reproduces the bound RT 16/16 exact on bind_s2): inverter 67..76 (RT20 66..74),
     all <= 95.
  W / DQ / RL (main regen_constants.kv_vport formulas through the landed-stage model; on bind_s2 it reproduces
     CFG_FIA 137 and the 12 DQ>15 vports of kv_constants_s2 [CHECKED model]): inverter RL 135 (RT20 132), FIA 140,
     DQ max 65, 12/16 vports > 15, W pads 302 stages (max 50) x 15 bits ~ 4.5k FF; per pv type the two vports are
     different leaves of one partition (span 0-7), so the pads are type-constant, no strap site needed.
  tok/s: +3 PV round-trip cycles vs RT20 (+62 vs bind4) -> 36 cyc/token per cycle/layer (accepted_cost DAG):
     ~4020.7 tok/s = -0.75 % vs 4051.0 (UNCHECKED estimate; < 5 % -> no OWNER question).  W pads add 0 cycles (RL kept).

(3) W-LANE PAD GENERATOR (physical/die_plan/qwen_kvsys/r8/vport_w_pads.py, die-local, new): pads from the MAIN
  regen_constants.kv_vport VPORT_DQ on a bind (one model), pad = DQ-15 on pr_t+pr_valid as an r8_extra.v1 table for
  asbuilt.land_r8_extra; RL unchanged by construction.  Replaces the stale hand table r8_position_2144/vport_request_extra.
  On bind_s2 (RT20): 12 vports padded, 270 stages, max 45, 4,050 FF, RL 132 -> 132.  Dry-run strict bind of the RT20
  event with it: see (5).

(4) MEASURED FALL ARRIVALS (task 2/4 prep; INFO only, the gate of record waits for FLOW-ONEMODEL-1 on main)
  grt13.sh: DIE-KV-12 combo GRT0 (inv r150) re-run with F (tap) / M (clock cell) falling-edge rows (FLOW-GEN-1 6672c5921
  form): rise T/N rows byte-identical to DIE-KV-12 (0 diff lines TT and FF) [CHECKED].  Max clock slew (all ck_* A/Y pins +
  taps, COORD 09:38 slew finding): TT rise 243.8 / fall 239.8 ps, FF 246.8 / 244.4 ps (< 320), 0 max-slew/cap violators.
  Fall - rise at taps: TT median -7.2 [-23.0, +12.8] ps, FF +12.7 [-14.9, +35.3] ps.  proof_fall/ = KV-12 proof + fall fields
  (tta_fall.py, lane-local copy of land-kv trial_tap_arrivals + F/M).
  FLOW-GEN-1 6672c5921 (git archive fg1/, NOT main) INFO:
   - its gate on ev1 (no measured fall in proof): CA TT/FF 0 fail (min 106.2/113.7, L678_0 fixed by the region-key fix) but
     start-skew 57/189 FAIL both corners = every fall-edge start port, "without a measured fall arrival" (fail closed).
   - its phase PLAN on proof_fall (measured fall): fall tree edges 57 -> 0, regions 190 -> 201, clean tree edges 170/200,
     max path ambiguity 0 -> 15 cycles, 116 crossings FAIL (unreached) -> no bind.  Same planner on the rise+T/2 proof:
     0 FAIL.  Likely cause (code read, UNCHECKED by experiment): fall samples take NO CPPR credit (fall_taps ->
     count_align_d_intervals(cppr_range=None)); KV common clock paths are up to ~14 ns, so the fall sample interval
     loses the whole common-path OCV and the planner abandons every fall edge.  -> FLOW-ONEMODEL-1 input.

(5) W-PAD DRY-RUN STRICT BIND (RT20 event_ectl plan + recipe_kv13_s2wpad = recipe_kv8 + land_r8_extra vport_w_pads_s2.json,
  ot-run intel1, 1408708b80 clean): the pad table lands (extra_tables replaced 24 = 12 vports x pr_t/pr_valid, stale 0,
  uncovered 0) but the bind has 1 error, NOT from the pads:
    EMIT kv3_hg: fclk_out_ft1_o contract source_clock_port clk_t4 is not an input port of the type
  Cause: ROOT-MERGE-125 (DIE-HEAD-9 74e4640935, fclk_out_o RTL source = landing contract source_clock_port) is newer than
  the DIE-KV-7 event_ectl sidecar (made 10-28 early; DIE-KV-8 bind_s2 on e9060685 had 0 errors).  The inverter event
  will be composed on current tools, so it gets a matching contract; the RT20 sidecar is stale for current main.
  [CHECKED: bind_report errors / extra_tables]
OPEN: step 5 bind/R8/pads/image/token sim (needs compose start pins, DIE-HEAD-11); gate of record + width plan on main
  (need QC-11/KV-12/FLOW-ONEMODEL-1 merged).
