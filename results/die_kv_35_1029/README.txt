DIE-KV-35 (2026-10-29 14:37-15:15 PDT) KV die owner, receipts. Runs intel1 /srv/opentallas-scratch2/claude/die-kv-35-1029
(tools = main 49d8a0c889 tools/die_plan via wt/die-kv-33-leaf; count_align/die_sta_related unchanged on main since).

KV-021 (CA on leaf-A arrivals; COORD 14:37 ruling (2): planner picks K)
 1. d intervals: regen_d.py = main count_align_plan.load_rows + sta_rows_hull (gate per-port interval, table OCV, shared
    droop, spice_edge, inv, CPPR LCA).  RECIPE CHECK: on the record proof_mixed + hm_r26q15c it reproduces
    codex-kv-1028/ca_mixed_replan.json d_lo/d_hi/wander exactly (max |delta| 0, 0/3595 ports) [CHECKED regen.log].
    regen_d2.py = same, hull over BOTH gate calibrations (spice_edge U spice_cell) -> ca_A2_replan.json.
 2. Control: native6 plan_native.py with main tools on the native6 inputs reproduces native6 native_bind K/depth/sched/
    origins exactly (diff_control.txt: 0 ports, 0 parts) [CHECKED].
 3. proofA replan WITHOUT --start-prev (diff_nativeA_noprev.txt): 381 port K changes, 19 origins -1, 27 start-edge
    EDGE_FALL flips (start tree re-picked on the moved arrivals) = NOT the expected 86 -> stopped (brief stop rule).
    With the existing FLOW-GEN-2 --start-prev option (prev = native6 plan; plan_native_startprev.py): 0 origin / 0 start
    edge / 0 part changes.  Edge-only hull (nativeAp): the 86 expected ports K+1 + io_W3->sys_c 12 ports K-1; gate PASS
    spice_edge TT 116.5 / FF 107.0 but spice_cell FAIL TT 73.8 / FF 82.2 (16 ports).  Both-cal hull (nativeAp2): 125
    ports K+1 (diff_nativeAp2.txt), no K-1.
 4. Event bind eA2 (mk_event.py: the same ECTL equalisation compose_native.py applies, equalised to the event26 target;
    3 ECTL extras absorbed: L382_0, L366_0, L434_0): 122 ports K+1 vs event26, sched 9341->9463 (+122), regions/parts/
    start tree unchanged; verify 3595 cycles, 0 identity/loop errors, 0 sim window violations, min lo 105.1 / hi 444.1
    (verify.json).  Die STA (gate.sh = DIE-KV-34 recipe, CA = eA2 bind, proofA): spice_edge TT lo 128.5 hi 488.0 /
    FF 113.8 / 492.7 PASS; spice_cell TT 105.0 / 453.3, FF 105.2 / 445.3 PASS; start-skew 0/1687 fail both; intra TT
    setup 297.35 (edge) / 289.36 (cell); hold UNMEASURED (no kit views) (sta_Ev2_*.summary.txt) [CHECKED-own readout].
 5. Straps (count_align_bind.strap_ties on the event27f plan): 0 strap pin/width changes; 14 instances re-tied on 9 types
    (hg_v1, hg_v1p3, hg_v1p6, hroot, hub_Wo, pc_v1__cl23f6a148, pc_v1__cl4ea58a5c, pc_v1__cl7f648944, pc_v3); LEC
    variants 131->132 (pc_v1__cl7f648944 11->12).  summary.json lists every port and instance tie delta.
 6. strap_lec.py (gen_rtl form) cannot build KV types: GenError 'bus not bound to any leaf port' (hub_Wo i_ahub_am_WN,
    hg_v1 o_ectl_Q_N_eN); KV kits are bind.py kit-rtl (bound netlist), not gen_rtl wrappers.  Strap LEC for KV = the
    bind route (recipe_kv27f_eA2.json = recipe_kv27f with clock_landing_table -> eA2 sidecar) + per-type kit-rtl diff.

KV-022 (helper): clk_clk_phy declared with the existing clock.edge_clocks form (die_plan_sd35_delta.json); both kits regen
 rc 0, kit_preflight PASS 0 issues, port_bind PASS 1086/1086 + 1084/1084 [CHECKED]; place LIVE epyc2.  Island re-site
 estimate islands/isl_est2.json: 151 windows on the macro+halo per type = 46 clock cells + 105 reset/start relay cells;
 reset/start relays re-sited along the E rim + S rim keep 7 stages (mean leg 306 um < 405) [geometry CHECKED, no schedule
 effect UNCHECKED]; clock cells -> short S-rim tree (~4 repeaters) needs a die clock tool rerun with the macro blockage
 [UNCHECKED].  Note: edge_clocks times clk_phy at the die period 833 ps (PLL model 1043 ps) = tighter, CDC timed as sync.
