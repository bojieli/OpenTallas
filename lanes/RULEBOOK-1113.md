# RULEBOOK 11-13: family design rules set by Fable expert lanes

The owner (11-13 03:4x) asked Fable expert lanes to set the few family-level physical design rules that keep recurring, once, up front. COORD and every lane follow these rules. Each rule has an ID, the rule, why, the implementation (tool and sha), its proof kits, and the dies and types it touches. Only the owning Fable lane edits its own section.

Expert review evidence: ~/coord/lanes/EXPERT-REVIEW-1.md

## R-CLOCK (HOLD-TAP-1): kit hold debt is built once, on the balanced tap trees, before the first global route

Status 2026-11-13 07:17 PST (R-CLOCK-1 opt-in per COORD 07:2x ruling, HOLDTAP-FIN-2; was 05:40). Owner HOLD-TAP-1 -> HOLDTAP-FIN-2. Implementation: branch claude/hold-tap-1-1113@e390ae79d7 (hub; 6 commits on origin/main 23aaa6e1de, merge train 44), tools/die_plan/pregrt_ff_hold.py + gen_phys.py (config.mk lines, run_kit.sh step) + schema; kit_preflight.py core_tap_reach (R-CLOCK-5). Evidence: lanes/HOLD-TAP-1/.

### What was wrong (measured; this replaces the "insertion mismatch" reading of the class)
1. There is NO 120-185 ps tap insertion mismatch. 4_cts_final.rpt is written BEFORE cts_post.tcl (tap_balance.tcl), so it shows the unbalanced CTS trees. After the balance the tap means sit in the window: hd_turn_b 435..458 (target 450), QC sle_st_a 229..265 (250), S81 t41 175..269 (250). NEVER read 4_cts_final.rpt for clock insertion; read the OT_TAP_BALANCE / OT_TAP_RC log lines.
2. The "negative source latency" on the launch tap is the kit tap WINDOW (gen_phys.tap_window_tcl: `set_clock_latency -source -early -W_p / -late 0` per tap port), a contract with the die clock, not an offset. A pair on two tap ports pays the launch port's W_p in full (OpenSTA has no CRPR across ports); a pair on one port pays nothing.
3. So the hold debt of a kit is a CONTRACT quantity, known as soon as the trees are balanced. FF hold violators on the balanced post-CTS database, by class:

   | kit | total | port_in | port_out | same_tap | cross_tap |
   |---|---|---|---|---|---|
   | HEAD hd_turn_b (flat W 40) | 2,312 | 2,278 (ws -117.9) | 0 | 0 | 34 (-9.1) |
   | S81 slice_station t41 (W_p 18-51) | 7,049 | 4,817 (-68.2) | 2,220 (-34.4) | 9 (-10.7) | 4 (-12.9) |
   | QC sle_st_a_v1__cl67389ecd (flat W 50) | 11,403 | 1,038 (-109.3) | 1,330 (-21.0) | 563 (-35.8) | 8,472 (-79.4; median -14.5; median distance 11 um) |

   t41 and hd_turn_b are seam-contract port padding (in_min -40 / -90); only QC st_a is a cross-tap population.
4. The flow left all of it to the in-flow GRT repair, which re-routes per buffer: QC sle_st_a 1,384 buffers in 9,432 s, t41 never finished inside the time cap. The builds ended on OT_HOLD_STALL / the GRT time cap, and the cross-tap pairs that the GRT repair did close to 0 lost 14-31 ps at detailed route (hd_turn_b -14.07 on 25).

### The rule
R-CLOCK-1 (tool, OPT-IN per type, default OFF; COORD 11-13 07:2x ruling on train 44). A type whose plan sets `clock.pregrt_ff_hold: true` runs the HOLD BUILD right after the post-CTS hold gate and before the first GRT: FF hold repair on 4_cts.odb, placement parasitics, two scenes (TC setup + BC hold, so no TT setup is spent on a hold cell), clock cells FIRM. Two passes: (A) every path to +5 ps (ports = the seam contract, and same-tap pairs); (B) CROSS-TAP pairs only to +45 ps, the route guard. The guard is cross-tap only on purpose: a uniform guard above ~25 ps pads every ordinary zero-logic pair of the kit (hd_turn_b: 1,014 cells at 25, 2,678 at 28, 3,319 at 35 and TT setup 104 -> 43). The step is advisory: a tool error, a TT setup loss or no gain leaves 4_cts.odb unchanged (`OT_PREGRT_FF_HOLD FALLBACK` in pregrt_ff_hold.log) and the GRT repair works as before; every fallback also prints one classified line `PREGRT_HOLD_FALLBACK tool rc N` (tool error) or `PREGRT_HOLD_FALLBACK guard <reason>` (setup loss / no gain) in run_<goal>.log, which autopilot records on the job as pregrt_hold_fallback (advisory: the job's class is unchanged). Sign-off FF hold >= 0 stays the only gate. Turn on per type: plan `clock.pregrt_ff_hold: true` (absent or false = off, kit as before this rule); turning it on for a die follows a signed t41 proof and the die owner's plan event. Guard per type: `clock.pregrt_hold_guard_ps` (0-100, default 45).

R-CLOCK-2 (die owner, reading). pregrt_ff_hold.log prints one class line before and one after:
`OT_PREGRT_FF_HOLD class before port_in N ws X same_tap N ws X cross_tap N ws X port_out N ws X`. Act on it at the next plan event, in this order:
   a. cross_tap count above ~5 % of the kit's registers (guidance, QC sle_st_a is at ~10 %): the tap boundaries cut pipelines. Turn on / widen `clock.tap_pair_affinity` (QC and S81 have it; HEAD does not), and give the type a MEASURED `clock.tap_window.per_port_ps` at the die clock proof instead of the flat fallback (die_sta_related --kit-window-out + tap_window_floor.py). A flat window is legal; it is paid by every cross-tap pair of the type.
   b. endpoints left in pregrt_ff_hold_open.tsv after the build (setup does not allow the pad): these are the ONLY pairs that need a structural form. Zero-logic hop: lockup latch (`clock.ft_hop_lockup.types`, `reset.relay_lockup`, kit_zl_lockup.py) when T/2 - W_p - tree skew covers data + setup; else the full-cycle hop flop (ft_xtap.py, +1 cycle, pre-approved). Logic path: +1 register.
   c. W_p above ~100 ps on a type (>= 3 hold cells per cross-tap bit): fix the die clock for that region (neighbour taps on one spine branch, METHODOLOGY 3.7); do not pad it.
   d. port_in / port_out: seam contract, built to +5; die STA judges them against the parent (NEEDS_PARENT). No action in the kit.
R-CLOCK-3 (no new per-kit hold forms). ZLP (kit_zl_hold_pad.py), per-endpoint face_hold_pad tables and item `--hold-ff-margin` arguments are not added to new kits; the build covers their cases. Kits already signed with them stay as signed.
R-CLOCK-4 (stall = structure). After this rule an OT_HOLD_STALL or OT_HOLD_STRUCTURAL at GRT is a real structural case: pregrt_ff_hold_open.tsv names the endpoints. Do not retry the kit and do not raise the caps.
R-CLOCK-5 (core taps: the port sits at its own core; tool check, blocking). An early core tap port clk_c<k> drives ONE hard-core clock pin. CTS skips a single-sink net, so the port -> pin leg is one unbuffered wire and its delay is not in the tap's early latency. Rule: the plan's core tap xy is at the clock pin of the core it names (0-50 um from the core outline on every correct tap measured). Kit preflight check `core_tap_reach` (kit_preflight.py, reads the kit's core_taps.txt, io.tcl, macro_place.tcl and macros/*.lef) stops a kit in seconds with `FAIL_PREFLOOR kit_preflight` when a single-pin core tap is more than 300 um from its core, and names the core the port sits at. `export OT_CORE_TAP_REACH_UM = N` in config.mk changes the limit, 0 turns it off. This is the S81 leaf class (COORD 05:4x: t35, t41, t56, t54, t73, t60, t61, t53 stopped by the post-CTS FF hold gate at -334..-432 ps). It is a different class from R-CLOCK-1: the hold build does not cover it and must not (the gate stops these kits first, and -400 ps is a wrong clock, not a pad job). Measured on ot_s81sl_leaf__t41 (wave 7073a6b4a59 attempt_3): the 9 other core taps are 0-41 um from their cores; 12 of the 16 u_vp.g_ln[k].u_l taps sit on ANOTHER ln core's site, 135-939 um from their own (clk_c16 drives ln[1] from ln[12]'s site, clk_c23 drives ln[8] from ln[1]'s site). The leg delay follows the distance: 6 um 0 ps, 383 um 155 ps, 486 um 196 ps, 939 um 470 ps. Core ln[1] therefore captures at 729 ps against the 250 target; 5,325 register pairs fail, all 496 below -200 ps launch on grid tap clk_t21 (425), clk_t8 (67) or clk_t4 (4) and capture in a hard core (worst: ln[1]). tap_balance already printed it (`OT_TAP_CORE ... WARN early core tap still late`, 20 of 27 pins; tap means 197..729) but a WARN stops nothing. Same form in 26 of the 27 ot_s81sl_leaf kits on epyc9 (every one but t2; 4-11 taps over 300 um each), table lanes/HOLD-TAP-1/core_tap_reach_epyc9.tsv. ACTION DIE-S81-87: in the prepared wave plan the ln core tap xy and the ln core sites disagree (physical/die_plan/s81/die_plan.json on main carries no early core taps for this type, so the binding appears to be made in the wave preparation; not traced further here); re-bind each ln tap to the core at its xy (or move the taps), re-kit the leaf family once, and do not relaunch leaf kits before that: they cannot pass. Also over the note level: HBM q_b001 (1 tap at 359 um) and 100-300 um on q_b000 / q_b010 / q_b011 / q_b100 / q_b103 and QC sle_su_c (277 um; it stopped at the same gate at -410 ps on 11-12).
For RULES-FLOW-1 (GRT hold repair settings): keep hold_guard_grt.tcl, the HB4 pad and the GRT hold margin (OT_HOLD_FF_MARGIN 0 / HOLD_SLACK_MARGIN) as they are; the build runs before them and they take the residue (hd_turn_b: GRT starts at hold +8.7 / 0 violators instead of -126 / 2,289). Do NOT raise the GRT hold margin uniformly: ports are built to +5, so a GRT margin above 5 sends every port bit back through the slow GRT repair. Measured placement -> routed hold loss per pair on hd_turn_b: cross-tap median -0.9, p90 11.5, p99 26.5 ps; same-tap p99 11.0 ps; GRT -> routed 5.7 ps on the worst unpadded pair (+8.7 -> +3.0). If you want more routed margin, the lever is a register-to-register-only margin at GRT (port hold excepted for that pass, as the build does); that is not built here. Two reading notes against R-FLOW-5: (1) its "no hold repair after CTS" is the ORFS CTS-stage repair_timing (SKIP_CTS_REPAIR_TIMING stays 1); the hold build is the separate two-scene step it refers to. (2) The build names its cells hold* and prints `hold_cells N` in pregrt_ff_hold.log; the R-FLOW OT_HOLD_BUDGET line should count them together with the GRT repair cells (hd_turn_b: 1,150 built + 0 at GRT of 31,907 instances = 3.6 %).

### Proof
All runs private, DO_NOT_COUNT. Kits are copies of other lanes' proof kits plus the build (prep_proof.py in the evidence), run through ot-run on epyc9 from CTS to sign-off.
- HEAD hd_turn_b (copy of CLAND-RELAY-3 proof_turn_b_wc16; epyc9 /srv/opentallas-scratch2/claude/hold-tap-1/proof/tb45). Before: GRT repair from -126.22 / 2,289 to +0.45, routed FF hold -14.07 on 25 endpoints (all cross-tap u_ft_t_s0 -> u_ft_t_s1), TT setup +104.02, not signed off on that class. With the rule (guard 45): build 12 s, 1,150 hold cells, GRT starts at hold +8.66 / 0 violators, SIGNOFF LOCAL_PASS_NEEDS_PARENT: TT setup +101.32 (-2.7 ps), FF hold +3.00 / 0 violators, DRC 0, antenna 0. NEEDS_PARENT is io_hold_parent (die level, as before). The cross-tap u_ft_t_s0 -> u_ft_t_s1 hops route at >= +17.0. Also run: guard 35 (+3.66, TT +101.88), uniform register-to-register guard 25 (+2.71, TT +101.46) and uniform 35 (+1.82, TT +44.7: rejected form).
- S81 slice_station__t41 (copy of the RELAY-PLACE-1 FT-LANE kit; epyc9 hold-tap-1/proof/t41). Before: GRT hold repair started at -61.92 / 6,868 and ended on the GRT time cap after ~8 h, not signed off. Build alone on a copy of 4_cts.odb: 7,049 -> 0 violators, 12,805 hold cells, TT setup 124.64 unchanged, 1,267 s. Full CTS -> sign-off run: in-flow build DONE (7,049 -> 0 violators, 9,540 hold cells, 816 s, TT setup 124.64 unchanged); GRT / route RUNNING, result appended here and in the READY.
- QC sle_st_a_v1__cl67389ecd (slim copy of the failing attempt_3 kit; epyc4 hold-tap-1/proof/sle_x45, final form guard 45): build alone on its 4_cts.odb: DONE (2026-11-13 07:12 PST, HOLDTAP-FIN-2). 11,403 -> 517 FF hold violators (before: port_in 1,038 ws -109.34 / same_tap 563 ws -35.81 / cross_tap 8,472 ws -79.37 / port_out 1,330 ws -21.04; after: port_in 517 ws -96.35, same_tap 0, cross_tap 0 (cross-tap worst +45.0 = the guard), port_out 0), 38,909 hold cells, 557,043 insts, 9,110 s. TT setup WNS -464.73 before and after (two-scene build spent no setup). The 517 left are input-port endpoints on paths whose TT setup is already negative, which the build refuses to pad: they are the open list (R-CLOCK-2b), not a pad job; the kit's -465 ps TT setup is its own (R-RTL / plan) problem. Build only, no route / sign-off run on this kit.
- Tests: tools/die_plan/test_pregrt_ff_hold.py (14), test_grt_goal.py (6) and test_core_tap_reach.py (8) pass; the 27 existing kit_preflight tests pass. The 271 gen_phys / run_kit test files of tools/die_plan and the 14 of tools/autopilot give the same failing set on the branch and on origin/main (sparse tree, serial run) except test_die_sta_related.py::test_exact_canonical_period_and_noncanonical_policy and ::test_related_helpers_share_exact_period, which fail only inside the long serial run and pass alone on both trees (order dependent, not touched by this branch).

### Affected types per die
The build is on only for types whose plan sets `clock.pregrt_ff_hold: true`, at their next kit generation (config.mk gains `export OT_PREGRT_FF_HOLD = 1` and `export OT_PREGRT_HOLD_GUARD = 45`; the kit gains pregrt_ff_hold.tcl). Kits in flight are not touched. Types known to be in the class (autopilot FAILED lines since 11-10 plus the lanes' private proofs):
- HEAD (s81_head): hd_turn_b (routed -14.07 on 25 cross-tap), hd_st_n4 (OT_HOLD_STALL -5.84 / 324), hd_mesh (15,136) and hd_spn_end (-9.75 / ~4,658) as reported by RELAY-PLACE-1 (their reports were overwritten by the rp18r2 rebuild; not re-measured here); hd_tile already had the opt-in form. HEAD has no tap_pair_affinity: R-CLOCK-2a applies first to hd_mesh and hd_spn_end.
- QC (qwen_compute): sle_st_a_v1__cl67389ecd, sle_st_a_v1__cl989804f6__cled3c1d7b, sle_st_a_v2, slw_st_a_v1__clfc5867a6__pvdf8e5ca4, slw_st_a_v1__clfc5867a6__pvf82a6c28, slw_st_a_v2__cl9f076a5c (all OT_HOLD_STALL at GRT, -91..-112 ps, 10,421..15,692 endpoints). Candidates, cause not split here (GRT time cap): slw_fw_v1__clf51c11d8__cl592e3d37, slw_fw_v1__clf51c11d8__clc7ddab13. Note: sle_st_a also has TT setup -507 ps at CTS (36 endpoints at GRT); that is not this rule.
- S81 leaf family, R-CLOCK-5 class (NOT the hold build; needs the plan re-bind): ot_s81sl_leaf t6, t7, t12, t13, t21, t22, t25 (x2), t28, t29, t30, t34, t35, t39, t40, t41, t47, t50, t51, t55, t56, t61, t65, t72, t73, t74 measured on epyc9; t53, t54, t60 (COORD list; kits on other hosts, same family, not measured). The slice_station__t41 proof below is a different type and does not cover them.
- S81: slice_station__t41 (GRT time cap, -61.9 / 6,868; port contract). The other slice_station types (t27 / t36 / t37 / t43 / t52 share its form) are expected in the class; not measured here. Candidates (GRT time cap): ot_s81sl_leaf__t21, ot_s81sl_leaf__t56, serdes__t2.
- HBM, KV: no kit in the stall class since 11-10. NOT in the class and not helped by the build: kits stopped by the post-CTS structural gate (FF hold below -200 ps - W), e.g. hbm ot_hbm_svc_sm_xcal_rel_t (-264.7 / 105), the QC cb*_q* and sle/slw_su rows, kv3_hg_v1p4; they need R-CLOCK-2b/2c forms.

## R-RTL (HARD-S81-SERDES-1): pipelining depth for paths over budget
Written 2026-11-13 03:29 PST by HARD-S81-SERDES-1. Status: rule text final (S81 rows updated 11-13 07:4x with measured cones); the S81 serdes and seqhost proof builds are still running (see lanes/handoff/HARD-S81-SERDES-1.md). Numbers are read from existing reports (TIMING-CLASS-1 census 11-12, serdes__t2 attempt_27 4_cts_final.rpt, CORES-HBM-1 rx_bm3 probe); I ran no new STA sweep over the dies.

**R-RTL-1 stage budget (833 ps, TT).** 833 - 60 uncertainty - clk->Q 60..90 - setup ~25 leaves about 650 ps; keep 50 for skew, so 600 ps for cells plus wire. Measured cost: 29..34 ps per logic cell at light load (hidx 757 ps / 22, svc_vm 794 / 27, serdes am_ok 203 / 6), about 60 ps per cell when a cell drives 80+ loads (hd_host_w 617 / 10), about 0.8 ps per um of repeated wire (serdes u_txl 1267..1674 ps over 1.7..2.2 mm). A stage must fit
`32 ps x logic cells + 0.8 ps x um (pin to pin, Manhattan) + fanout terms <= 600 ps`. As a table:

| launch-to-capture distance | max logic cells (buffers not counted) |
|---|---|
| <= 100 um | 16 |
| <= 250 um | 10 |
| 250..405 um | 3 (mux / enable only: this is a relay hop) |
| > 405 um | 0, and one register row per 405 um (12.1e) |

**R-RTL-2 fanout inside a stage.** A net with more than 64 loads is not one cell: give each group of <= 64 loads its own registered copy of the source (enable, select, reset, valid). The copy is placed with its loads. Never close a wide broadcast with buffers.

**R-RTL-3 macro ports.** After a memory or hard-core output (clk->Q measured 365 ps on the serdes dmem): at most 5 cells and 100 um before the next register; if not, register at the port and read one address earlier (0 cycles) or take +1 cycle. Before a macro input (setup 131..194 ps measured): at most 8 cells and 100 um.

**R-RTL-4 where the check runs.** (a) At synthesis, before any place and route: count non-buffer cells per endpoint on the 1_synth netlist (STA with zero wire). Any endpoint over 16 cells or 520 ps of cell delay is an RTL item; the kit does not go to placement. (b) At placement, split every failing path into logic / repeater / wire. Repeater + wire > logic means the path is a reach or placement item (R-REACH, lane rows), not a depth item; adding logic stages will not fix it and rebuilding will not either.

**R-RTL-5 the fix, in this order.** (1) Restructure the cone: parallel-prefix instead of ripple, balanced tree instead of chain, registered partial products for wide XOR matrices. 0 cycles. (2) Retime an existing register into the cone. 0 cycles. (3) Add a register stage, +1 cycle (owner pre-approved). No settings, retries, ECOs or relaxed constraints in place of these.

**R-RTL-6 latency bookkeeping for every added stage.**
- The stage is a parameter or define, default off; default off must be flop-for-flop the old netlist.
- Data, valid and the reset that defines the frame or calendar move by the same edges. A stage that moves data but not its reset is a bug even when a loopback still passes.
- One lock-step bench per form: new(t + N) == old(t) on every edge outside reset, through cold reset, warm reset and any local reset sequencer. The bench also carries at least one mutant (a row short, or a reset not moved) and one wrong expected N; both must FAIL.
- One row per added cycle in results/<lane>/latency_rows.json: id, lane, parameter, added_cycles, clock, relative_to. The row goes to the die owner and TOK-VERIFY with the READY.
- The plan type carries the parameter (verilog_defines); after the bind, tools/die_plan/lane_asbuilt_latency.py must PASS on the bound plan. Internal stages of a link (serdes, PHY) that the lane table does not count are still reported as rows.
- Registers added for reach are placed by rule (FIRM at their per-bit lane site before global placement), never left to wirelength-driven placement: it puts all rows of a 2-pin chain at one end.

**Types over the rule today** (source in brackets; "unmeasured" means no path report exists, not that the type passes):
- HBM ot_hidx_s3_q: 22 cells 757 ps, TT -203.5, 160 endpoints. R-RTL-1. Fix: prefix adder for the s3 sum, else +1 stage. [TIMING-CLASS-1]
- HBM ot_hbm_svc_vm_kshare_splitstrap__v700685: 27 cells 794 ps, TT -36.2. R-RTL-1. Fix: balanced priority tree or retime sm_s. [TIMING-CLASS-1]
- HBM ot_hbm_svc_vm_kshare_splitstrap__v8e478a: fanout-64 c_k_rdy broadcast, 475 ps of buffers, TT -68.0. R-RTL-2. [TIMING-CLASS-1]
- HBM hnx_fused_lane_c: e_rd -> SRAM wd_in, 134..291 ps single cell + 137..219 ps pin net + SRAM setup, TT -251.9. R-RTL-3. [TIMING-CLASS-1]
- HBM ot_pdie_serdes_rx_bm3_rest (5 instances): 296 endpoints sc_q -> sp (8 XNOR levels behind 100 + 135 ps fanout buffers), 90 in the rate matcher, TT -171.7. R-RTL-1 and R-RTL-2. Fix forms exist (SPCYC, OT_S81_RM_STAGED), in build by CORES-HBM-1. [CORES-HBM-1 11-12 03:47]
- HEAD hd_host_w: 10 cells 617 ps with fanout-84 and fanout-86 enables, TT -76.2. R-RTL-2. [TIMING-CLASS-1]
- HEAD hd_serdes: FAIL 11-12; same KP4 encoder / syndrome RTL as S81, cones unmeasured by me.
- S81 serdes family, 11 types / 14 instances (one shared column RTL). Three classes, all measured on serdes__t2 private kits (lane dir epyc9 /srv/opentallas-scratch2/claude/hard-s81-serdes-1): (a) R-RTL-1 row 4, reach: a27 u_txl r[0] -> q 0 cells / 1267..1674 ps of repeaters, PMA face -> u_syn 1570 ps; fixed by the LANE rows (PIN 3 / TXA 4 / RXI 5 / RXO 3, define OT_S81_SERDES_LANE, rows FIRM on per-bit lanes): no lane path in the failing list of kitA / kitB, planned hops 277..340 um. (b) R-RTL-2: u_rm rp_g2 -> push -> 4096-load mem write enable, 15..17 cells, 4091 endpoints (kitB TT -3595 at placement, before repair); u_syn S_q / ldr syndrome broadcast 2.6..2.8k endpoints -1300; lpl rq 1636 endpoints -330; enc rem_q 280 -244. Fix = the existing proven cone forms OT_S81_RM_STAGED + RM_LOCAL4 + RM_WFULL8, KP4_SYN_LOCAL, KP4_AM_FACE3, RST_TREE, CLAND_WCHK (kitC, in build). (c) geometry (DIEVIEW-S81 F5): island under the PMA at the port end, one template (tools/die_plan/serdes_template.py, 11 types PASS, max hop 337.5 um). Cycles: LANE +15, cone set +7 in loopback (88 -> 110).
- S81 seqhost__t1: depth, not reach (placement is compact). Measured on a9: u_win pe -> ts mux -> + eD -> == tm -> fire 24 cells 777 ps (TT -586, 606 endpoints); rp -> due 21 cells (-457); lw -> hcfg_bad -> rec -> table enables 18 cells, 3488 endpoints (-239). R-RTL-1 and R-RTL-2. Fix dsdv_mu_hwin LA (lookahead compares, kept pointer copies, registered payload, 0 cycles): placement TT -586 -> -284, 5270 -> 3863 endpoints; the rest of u_win is armed -> ss -> rec -> 47 x 63 write enables, 2983 endpoints -115 (R-RTL-2; form LA 4 in build). Host engine cones are NOT fixed and are over the rule: u_eng ap0_local -> ap1_lp 26 cells 898 ps (-182), ofree -> sp_acc 21 cells (-117), cq_rd -> cx_w 18 cells (-146..-173); fanout u_iss.hh 593 endpoints (-89). [lane dir sta_seqhost_a9, sta_kitS3]
- KV kv3_hub_Ei: 1 cell + 6 repeaters 745 ps, TT -159.5. Reach (R-REACH), not depth. Listed so it is not sent to RTL. [TIMING-CLASS-1]
- QC: the census has no QC setup rows; unmeasured against R-RTL-4a.
- HBM q_spb1, vsN1, vsN2 and the 10 S81 slice_station rows are clock-tap or hold items (R-CLOCK), not R-RTL.
## R-STREET (RULES-STREET-1): macro and pin-face streets, congestion escape
Written 2026-11-13 07:56 PST by RULES-STREET-1. Status: FINAL. Rule landed on main; counts final; both proofs measured.

**What it fixes.** GRT overflow is the largest structural class (103 CLASSIFY events). The renders show one cause: a macro stands close behind a face that carries thousands of the type's own pins, or station columns stand in 15-35 um slots between macros. STREET-RULE-1 (11-12) only counted the pins of the *cores* facing a gap, so a macro row 34.56 um above a 6.7k-pin face passed it. R-STREET adds the type's own pins and the stations to the same tool.

**Constant.** K = 37.5 routable tracks per um of street width (3 layers along the street, 0.048 um pitch, 0.6 fill; AUTO-GEOM's demand rule uses the same ~35/um for M2+M4 or M3+M5 at 0.75). All widths snap up to the 4.32 um lattice. A street is 43.2 um; a tap-legal slot is 17.28 um; abutted means < 4.32 um.

**R-STREET-1 macro to macro** (STREET-RULE-1, kept). Two facing macros either abut (pins go straight across, no cells between) or leave a street >= max(43.2, facing pins / 37.5) um. A face with more than 1,500 pins never abuts another pin face.

Ruling for abutted array tiles (HEAD-97 ask, 11-13): street capacity is never judged across a seam, because a tile cannot route in its neighbour. But the 43.2 floor of a core face that looks at the outline is for dense faces. A sparse face (under 3 core pins per um of face, and nothing planned standing in the strip: no station, relay column or tap) may keep max(8.64, pins / 37.5) um to the outline. hd_tile's 81-pin elemA faces (about 0.3 per um, 2.2 um of wire) at 12.96 um are legal; the zero-growth form 12.96 / 43.2 / 12.96 stands, with the 43.2 um spent on the middle street that holds the 490 pins and the pin relays. The tool still prints these as `outline_street` with need 43.2; read a sparse one as waived by this ruling until the tool carries the tier.

**R-STREET-2 macro to pin face** (new, check kind `face_street`). Macros (hard cores and LEF SRAM/ROM contents) nearer than 129.6 um to a face that carries the type's pins form *walls* along that face; two macros belong to one wall when the opening between them is under 43.2 um. For each wall: n = type pins of that face inside the wall span, ends = wall ends that open onto >= 43.2 um (0, 1 or 2). Every macro of the wall keeps

`gap to the face >= min(129.6, max(floor, n / (37.5 x ends)))`, and 129.6 when ends = 0,

with floor = 43.2 um when the wall is dense (n / wall length >= 3 pins per um; the failing S81 faces carry 4.0 to 5.4) and 17.28 um otherwise. Under 16 pins, or a wall shorter than 43.2 um, there is no demand and the plan edge margin stays legal. In numbers: at 5 pins/um a two-ended wall may be 648 um long at 43.2 um; a one-ended wall 324 um; beyond that the gap grows 4.32 um per 162 pins (one end) or 324 pins (two ends).

**R-STREET-3 abut instead, and move the pins.** A macro may abut a pin face (< 4.32 um) only when the pins in its span go straight into it (pins in span <= its own pins on that face + 16). Order of fixes for a `face_street`, cheapest first:
1. Move the pin window to a free span of the same face (the check prints `free_spans`) if the window still fits at <= 6 pins per um. Costs nothing, but both partitions of that face move together, so it is a die plan event.
2. Lift the macro to the need. `street_rule.py legalize` does this; it uses free area first and grows the outline only when there is none (growth is pre-approved).
3. If the need is over 86.4 um: break the wall. Open a >= 43.2 um cross street so each wall is two-ended and shadows <= 3,240 pins, then the need falls back to 43.2.
4. What is left goes over the cell on M8/M9 (X-TIER-OTC) where the macro obstruction stops at M7 or lower.

**R-STREET-4 where stations may sit** (new, check kind `station_alley`). Planned station registers (ft bit sites, ft registers, internal stations) sit in open area, in a street, or on their own core. A slot between two macros, or between a macro and the outline, that is narrower than 43.2 um and at least 43.2 um long may hold: nothing above 15 bits if it is under 17.28 um wide; under 3 bits per um of slot length if it is 17.28 to 43.2 um wide. A station column (>= 3 bits per um) needs a street. The fix is to widen the slot to a street (legalize does it) or to abut the pair and re-site the stations.

**Where columns may go (all dies).** A column is any row or column of registers that is planned, not placed by the tool: ft stations, internal stations, relay columns, reset relays, clock taps and their root buffers. A column stands (a) in open area, (b) in the middle of a street >= 43.2 um, at least 8.64 um off each macro edge, or (c) on its own core's bay. A column never stands in a slot under 43.2 um, and never in the strip between a macro and a dense pin face unless that strip meets R-STREET-2. A street that holds a column and also has core pins facing it is sized by R-STREET-1 on those pins, with 43.2 as the floor: hd_tile's elemA street (25.92 um, 490 facing pins, a relay column and 4 taps) needs 43.2. The tool counts ft and internal stations today; relay columns and taps follow the same rule by review until the plan lists them as stations.

**R-STREET-5 a station chain that runs along a slot: measure it, do not gate on it** (new, check kind `transit_street`, a WARN). Every planned hop (window to first station, station to station, last station to window, and internal stations) is a segment that carries the bits of its slot. A hop that runs along a slot between two macros, or between a macro and the outline, loads that slot. T = the largest sum of hop bits through one 43.2 um stretch of the slot. The target is

`width >= T / 37.5`.

In numbers: one 1,104-bit ft slot needs 30.24 um, two side by side 60.48, 3,400 bits 90.72, 4,250 bits 116.64. A pin-face strip that is used as an ft corridor is the common case: on S81 leaf t28 the strip between the S face and the macro row carries ft2 to ft12 sideways, 4,250 bits at x 237, in 34.56 um. This is a WARN, not an ERROR: on t28, widening every corridor to T / 37.5 on top of rules 2 and 4 cost +15.5% outline instead of +7.7% and cut the M4-M8 overflow only 13% further (see Proof). Use it when you draw a form: route a chain through open area or split it over two streets instead of along a face strip; `legalize --set transit_rule=1` widens the corridors if you want that. Putting the first and last station of a window inside the window span, within 30 um of the face (METHODOLOGY 1.9), removes the sideways run from the face strip altogether.

**R-STREET-6 halo.** No kit halo is added: kits keep `MACRO_PLACE_HALO 0 0`, and the plan gap is the halo. Between a macro and anything else the plan uses only three widths: abutted (< 4.32), tap-legal (>= 17.28, sparse pins and stations only) or street (>= 43.2). Gaps of 4.32 to 17.28 um stay a WARN (`sliver`) unless pins or stations use them; do not create new ones. Macro arrays (SRAM banks at 8.6 um pitch on hd_mesh, hd_host_w, hd_host_e; the S81 ln array at 15 um) are drawn as abutted blocks of up to 4 macros with a 43.2 um street between blocks, so every macro has one face on a street for its pins, its taps and its columns.

**Why these numbers.** A pin in the shadow of a macro must jog along the alley to the wall end before it can turn into the type, so the alley mouth carries n / ends wires; 43.2 um x 37.5 = 1,620 wires. The 43.2 floor on dense walls is the room for the pin registers, the station column and the clock tap that land there. Measured (S81 leaf t28 attempt_3, event 7073a6b4a59): the macro row stands 34.56 um above a 6,714-pin S face (5.4 per um) and the ln column 34.56 um behind 2,636 W pins; AUTO-GEOM reports channel_h 4.13 and channel_v 3.85 there, and the 15 um ln slots hold up to 4,444 station bits each. dsdv c1x t3: u_cap is 34.56 um behind 1,903 W pins and 2,570 S pins (4.4 per um); AUTO-GEOM channel_v 5.44 and channel_h 3.02 in those strips.

**Implementation.** One tool, `tools/die_plan/street_rule.py` (branch `claude/rules-street-1113`, sha 8dd3028a50, merged to main as 5eefdbe2fa (train 45); branched off main fbfb4fc6a6; tests in `test_street_rule.py`):
- `street_rule.py check PLAN --repo SRC --out J.json`: per type the counts, the worst cases, and for each `face_street` the wall, pins, ends, need and free spans. Types whose only macros are LEF contents are checked too. Types whose buses carry no window (qwen_kvsys) take the pins from the plan ports.
- `check.py --street-rule warn|error` (G0): the same check; `face_street` and `station_alley` are ERRORs under `error` (`transit_street` is a WARN), next to `street`, `wall`, `outline_street`.
- `street_rule.py legalize PLAN --out-plan NEW.json --event EV.json [--set add_regs=3]`: the auto-fix. It moves hard cores only (never a shape, never a LEF content macro), lifts them off the pin face, widens station slots, keeps every station register count, re-sites stations, and refuses a move that lands on a content macro, breaks reach, or needs more than +25% area. `--no-bins` makes a read-only dry run. `--set face_rule=0` gives the old STREET-RULE-1 result.
- A moved core changes the type's reset collector tree, so a legalized type needs the normal re-bind before its kit (same as any plan event).

**Proof.** Private builds under `/srv/opentallas-scratch2/claude/rules-street-1/` on epyc7 (no wave state touched). Base = wave plan `src_s81_main_7073a6b4a5/.../plan_h2_2249.json`. A legalized type needed a private strict re-bind of S81 (rc 0, 0 errors) because the reset tree follows the cores; then kit-rtl, prepare-stations, gen phys, `run_kit.sh place`, and GRT on the placed DB.

S81 leaf t28 (254k cells). Two forms from `street_rule.py legalize`, cores moved only, no shape change:
- A = rules 2 and 4: 12 face_street + 25 station_alley -> 0 / 0 in 2 passes, 27 cores moved, outline 1442.88 x 1226.88 -> 1442.88 x 1321.92 (+7.7%).
- B = A plus every transit corridor widened to T / 37.5: 5 passes, outline -> 1442.88 x 1416.96 (+15.5%).

One-shot GRT of the three placements, same deck as AUTO-GEOM (M2-M8, adjustment 0.25, 0 congestion iterations, epyc8 `rules-street-1/grt0/`):

| t28 | total overflow | M2 | M3 | M4-M8 | wirelength | routed nets |
|---|---|---|---|---|---|---|
| baseline (attempt_3) | 6,673,695 | 1,432,975 | 1,816,163 | 3,424,557 | 26.49 M um | 264,653 |
| A (rules 2, 4) | 3,716,743 (-44%) | 1,518,339 | 849,423 | 1,348,981 (-61%) | 15.73 M um | 208,536 |
| B (plus transit) | 4,250,160 (-36%) | 2,138,205 | 939,370 | 1,172,585 (-66%) | 15.32 M um | 208,378 |

What this shows, and what it does not. The street layers (M4-M8) lose 61% of their overflow and the wirelength falls 41% under rules 2 and 4. B buys little more for twice the growth, so rule 5 is a WARN. The overflow that remains is on M2/M3 in the pin-register row along the S and W faces (I viewed both density renders: the 15 um ln slots became streets at about 20% density and the strip behind the pins is empty, but the first 10 um at the face is still a 60-90% row). That row is cell density at the pin bar, not street width: it needs the pin registers spread or padded (R-FLOW) and the registers at their pins (t28 pin-register distance p90 is 261 um against the 30 um rule; R-REACH). Neither form is GRT-clean. The 50-iteration AUTO-GEOM probe was cut at its 5400 s wall without converging on all three: baseline in iteration 5, form A in iteration 10, form B in iteration 11 (same host, epyc7, under changing load, so read the iteration counts as a direction only). The net counts differ because buffering follows wirelength, and legalize re-sited the 335 stations, so part of the gain is station placement, not the gap alone. AUTO-GEOM's channel_h estimate did not move (4.13 baseline, 4.77 A, 4.01 B); it is taken in the first 20 um at the face, which is that pin-register row.

dsdv c1x t3 (650k cells, over the 400k cap). Plan level: 4 face_street -> 0, 5 cores moved, 0% growth (u_cap 34.56 -> 43.2 off S and 51.84 off W, u_xr moved to open a 56 um street to u_cap). No transit items. Re-bound, placed, render viewed (the W and S strips behind the pins carry no red knot, the logic cloud between u_cap, u_xr and the p wall is 20-60%). One-shot GRT, same deck:

| c1x t3 | total overflow | M2 | M3 | M4-M8 | wirelength | routed nets |
|---|---|---|---|---|---|---|
| baseline (attempt_1) | 5,511,983 | 952,416 | 2,091,222 | 2,468,345 | 58.76 M um | 667,156 |
| R-STREET form | 1,279,985 (-77%) | 85,859 | 386,250 | 807,876 (-67%) | 25.13 M um | 437,130 |

Peak overflow per gcell fell from 220 H / 200 V to 84 H / 50 V. Read this with care: the synthesized netlist is the same (identical synth statistics), but the placed design is 7% smaller in cell area and has a third fewer nets, because placement buffering follows wirelength; a 57% wirelength drop is more than two moved cores explain on their own, so this is one run against one run, not a controlled test of the gap alone. The 50-iteration probe: baseline cut in iteration 3 at 5400 s; the probe of the R-STREET form was started 15:43 UTC and was left running (result in epyc7 `rules-street-1/proof2/dsdv_slice_c1x_C__t3/geom/`). Still not GRT-clean, and still 1.6x the cell cap (R-CAP).

Drawings: `lanes/rules-street-1113/t28_plan_before_after.png` (form A), `c1x_t3_plan_before_after.png`. Renders: c1x epyc7 `rules-street-1/proof2/dsdv_slice_c1x_C__t3/gen/dsdv_slice_c1x_C__t3/run/layout_review/place/density.png` (md5 0afa0c56); t28 epyc7 `rules-street-1/proof2/ot_s81sl_leaf__t28/gen/ot_s81sl_leaf__t28/run/layout_review/place/density.png` (A, md5 0d38c985), `proof3/...` (B, md5 62790d0b).

**Affected types today** (wave plans of 11-13; violators = `face_street` or `station_alley`; `transit_street` is the WARN column; tables with the worst case and the fix per type in `lanes/rules-street-1113/`):

| die | types with macros | R-STREET violators | face_street | station_alley | transit_street (WARN) | what they need |
|---|---|---|---|---|---|---|
| S81 | 349 | 170 | 129 | 128 | 84 | all 74 `ot_s81sl_leaf` types, 54 `col_h9/h10` types, 9 `dsdv_slice_c1x_C`, 16 `svc_*` types, 4 `kv_leaf`, 13 single slice / phy types. Lift or move the window 116, break a wall 21, re-site an SRAM/ROM 17, pins under an abutted macro 2, station slots 128. WARN: 84 types with a transit corridor under T / 37.5 (median target 86.4 um). |
| HEAD | 7 | 0 | 0 | 0 | 0 | No new-kind violators, but 5 types break R-STREET-1 and the column rule (DIEVIEW-HEAD-1113 F1, F5): `hd_tile` (264 instances) elemA N-S street 25.92 um with 490 facing pins, a relay column and 4 taps, wants 43.2 (DRT-0255), plus 4 elemA cores 17.28 um off the outline with 81 pins each; `hd_mesh` 16 streets, 206 slivers at 8.6 um, 36 clusters with no tap-legal face; `hd_host_w` 8 streets, 103 slivers, 21 tap faces; `hd_host_e` 32 slivers, 9 outline streets; `hd_serdes` cmem 8.64 um from chn with 825 pins. Fix: re-block the SRAM arrays (abutted blocks, 43.2 streets) and open the hd_tile street. |
| QC | 73 | 30 | 30 | 0 | 12 | `sle/slw_sc` 9 (u_core 23.28 um behind 1.6-2.0k E pins, wants 43.2), `sle/slw_stm` 11 (tload macro 14.8-23.5 um under 1.4-1.6k N pins), `su_c` 3, `su_l1` 4 (two with a closed wall), `cbn_q00` 2, `coll_core` 1, WARN only: `cbf_q00_s2` (3,340 transit bits in 86.4 um). |
| KV | 50 | 21 | 7 | 17 | 0 | all 16 `kv3_pv` types (stations in a 14.74 um edge slot, wants 17.28: a 2.6 um move), `kv3_hub_Eo/Wi/Wo`, `kv3_hg_v3`, `kv3_hgi_v8` (macro 17-26 um behind 0.7-0.8k pins, wants 43.2). |

R-STREET-1 (core to core, STREET-RULE-1 kinds) is still open on S81 334, HEAD 5, QC 42, KV 23 types; the same tables and legalize cover it.

Read-only legalize dry run (`--no-bins --set add_regs=3`, per type, before the die-level re-checks): S81 310 of 334 violating types applied, 309 clean, median growth 6.3%, p90 14.7%, max 23%, 33 with no growth; 17 stopped on a LEF content macro in the way, 4 on ft reach. QC 0 of 30 applied (reset-contract and ft-reach checks stop them), so QC needs hand forms. KV not finished.

**For S81-FORMS-1 and the die owners.**
1. Run `street_rule.py check` on your plan and read your rows in the table.
2. Draw the form so that no macro is inside the R-STREET-2 gap of a pin face, walls are two-ended, station columns stand in streets, and ft chains do not run sideways along a face strip. Prefer moving a window, breaking a wall or re-routing a chain through open area over growth.
3. Run legalize for the remainder, re-bind, build. Fold it into your next plan event; the 48 h wave freeze stands, so no wave switch before 11-15 04:00.
4. How G0 runs it. `check.py --street-rule` is `off` by default and stays so (the rule reads every core pin table), so the flag must be passed: every G0 run of every die passes `--street-rule warn` now (it adds `street_gap` WARN lines and `summary.street_gap`, and never fails the gate); a die's plan event that claims R-STREET passes `--street-rule error`, and from that event on its G0 keeps `error`. Wrappers (kit-wave gen, event scripts, die CI) carry the flag per die; nothing is baselined, the open items are the violator tables.

**Not done / limits.** (1) The proof is two S81 types, one run each: both improve (overflow -44% and -77%) and neither is GRT-clean on streets alone. No QC, KV or HEAD type was built under the rule. (2) K = 37.5 per um and the 3 pins per um line come from the S81 leaf and c1x numbers. (3) The auto-fix grows S81 leaf outlines (t28 +7.7%); all leaf types share one slot, so growth is a die event and I did not estimate the die. A hand form that uses the empty NE 40% of the leaf slot is the better answer. (4) The check reads the plan: pins are uniform inside each window, hops are straight segments, relay columns and taps are not counted as stations yet. (5) Pin-bar cell density and pin-register distance are outside this rule (R-FLOW, R-REACH). (6) HBM was not counted (parked).

## R-REACH (RULES-REACH-1): fanout and reach locality, face-net buffering

Posted 2026-11-13 04:48, updated 2026-11-13 07:35 by RULES-REACH-1. Branch `claude/rules-reach-1-1113` @ ce0e50e4e7 (hub; train 47, approved by COORD). **Merging it changes no existing plan, kit or G0 verdict: every rule is opt-in** (see step 7). Tool: `tools/die_plan/reach_rules.py` (check / fix / census). Handoff: `lanes/handoff/RULES-REACH-1.md`.

**The rule in one line:** no register talks to anything more than 405 um away or to more than 48 loads; whatever must travel farther goes through registered relays planned at 340 um, and one script inserts them.

### The five rules and their numbers

| ID | Rule | Limit | Auto-fix | Otherwise |
|---|---|---|---|---|
| R-REACH-1 start_fan | One register (or one kept copy) drives <= 48 loads, all within 405 um. A wider control net is carried by registered relays and copied once per region (hub + its loads within 300 um). Checked on the count-aligned START fan: origin -> every input ring, origin -> every FSTART output pin. | 405 um per hop (sites chosen at <= 395, trunks planned at 340); 48 loads per copy | yes: `clock.landing_reader_start` / `landing_writer_start` with `share_trunk` | G0 finding |
| R-REACH-2 macro_barrier | A macro with a side >= 405 um is a barrier. Logic on both sides needs a registered stage on the way round. The type declares `reach_homes` (where the soft logic of each face bus sits) and every window -> home corridor over 405 um gets stations. | barrier 405 um; hop 405 um; k = ceil(L/340) - 1 stations, +k cycles | stations yes (`--rules 2`), once `reach_homes` is declared | G0 finding |
| R-REACH-3 bus_window | A bus window sits on the face nearest its consumer. | target <= 200 um; never > 405 um without stations (R3-INTERNAL) | no (window moves are plan events) | G0 WARNING + MOVE-WINDOW list, priced in bit-mm |
| R-REACH-4 fwd_source | A forwarded clock output takes the nearest tap of the type's current tap grid. Never the root when a nearer tap exists, never a tap that no longer exists. | tap -> pin <= 405 um | yes: re-point `source_clock_port` | G0 finding |
| R-REACH-5 even chains | The generated zero-logic chains (landing bin -> lane pad stages `u_lpad_*` / `u_pd<n>_*` -> consumer) are re-spaced to equal hops after global placement when a hop is over 405 um. | 405 um | yes: kits of a plan with `budgets.r_reach_even: true` (chain_even.tcl); plan-sited flops never move; a chain moves only if its worst hop shrinks | AUTO-GEOM r2r |

A G0 finding is a WARNING by default and an ERROR when the plan sets `budgets.r_reach: "error"`. Rule 3 is always a warning.

Cycles: rule 1 adds boot cycles only (reader K - depth, writer K + depth at the bind; data cycles 0). Rule 2 adds +k data cycles on the bus (pre-approved). Rules 4 and 5 add none.

### Why these numbers

- **405 um** is METHODOLOGY 12.1e (registered hop, every layer). **340 um** is the planning step the KV START corridors already use (`kv_start_corridor_event.STEP_UM`): it leaves room for legal sites.
- **48 loads**: CLAND-RELAY-2/3 measured 65 loads per copy at 331-336 ps routed slew (limit 320) and 33-48 loads clean. The kit gate stays at 64 (`reg_fanout_gate`); 48 is the design number.
- **Evidence for rule 1.** KV kv3_hub_Eo (wave kit, BAD 11-13 03:08): 3,236 of its 3,869 captures over 405 um are the START fan, from two flops of `u_cland_origin` (2,425 + 800 captures, up to 2,260 um). The plan had no START transport for this type. That is the family: KV has 27 types with rings past 405 um and no reader chain; QC 6; HEAD 1. The carrier already exists and is in use: `landing_reader_start` on 75 QC types, 24 KV and 19 HEAD. Train 34 (one relay per wide ring, at the ring) cuts the load count but leaves the origin -> relay hop at up to 2 mm.
- **Stale chains are the second cause.** QC s28: 23 of the 75 types with a reader chain have a hop over 405 um (e.g. `sle_st_b_v1`: hops 255 / 846 / 1,229 um, the band moved and the chain did not); KV 5 of 24. The check prices a chain at the sites the kit really uses (`landing_place._chain_clear_of_hard_cores`), so a stage planned inside a hard core is measured where it lands.
- **Evidence for rule 2.** KV kv3_sys_c: ucie_rom is 778 um wide, 41 face buses on 6 sides name no consumer, 5,491 captures over 900 um. The check finds exactly kv3_sys_c and kv3_hub_C (ahub 605 um) on KV.
- **Evidence for rule 3.** HBM q_su30 pv1: 83,144 buffers on 8,393 nets, about 10 per net, for 7.8k face bits that sit far from their cores (HBM-FORMS-1). Buffers ~ bits x distance / 150 um. On the current plans (buses with a named consumer only): QC 26.6k bit-mm (~177k buffers), S81 22.1k (~147k), KV 4.4k, HEAD 2.5k.
- **Evidence for rule 4.** QC-S28-RESID: 573 forwarded-clock hops over 404 um; 572 of them can take a nearer tap. The same check finds 534 pins on QC s28, 1,338 on KV (root-sourced, FWDCLK-1 form), 49 on S81, 10 on HEAD.
- **Evidence for rule 5.** S81 leaf t21: `u_bin_leafdn_i0 -> u_lpad q` 587 um on 104 captures; KV hub_Eo `u_lpad r -> q` 824 um; QC st_a `u_bin -> u_pd4` 748-783 um. GPL keeps the free pad flop at its fanout and pays the distance in one hop.

### How to apply (every die owner; no questions needed)

Run from the tree root of a checkout that has the branch (or main after the merge).

1. **Check.** `python3 tools/die_plan/reach_rules.py check PLAN.json --repo . --tsv r_reach.tsv`. Exit 1 = errors. G0 (`check.py`) runs the same check; findings are check `r_reach`.
2. **Fix rules 1 and 4.** `python3 tools/die_plan/reach_rules.py fix PLAN.json --repo . --out-plan NEW.json --report REP.json` (default `--rules 1,4`; `--types RE` narrows it). Idempotent. A type it cannot fix is listed NOT FIXED and keeps its base form; exit 2. In a compose chain use `reach_fix.py fix ... --classes 1,2,3,4,5,7,8` (7 = rule 1, 8 = rule 4, run last).
3. **Bind strictly** (K - reader depth / K + writer depth are recomputed there; `clock_landing_verify` knows the shared trunk). Then the raw-reset branches of the START consumers, as before: `kv_start_corridor_event.py raw` (KV) or the die's own raw step. Run the lane latency check; boot cycles move, data cycles do not.
4. **Rule 2.** For each type the check names: add `reach_homes: [{"name": "...", "rect_um": [x0, y0, x1, y1], "buses": ["bus", ...]}]` to the type (the box where that soft logic is to be placed; `"*"` = all buses), or move the windows to the consumer's side. Then `fix --rules 2` adds the `internal_stations` chains; re-price the lane cycles (`reach_fix.sync_fixed_cycles`).
5. **Rule 3.** Read the `window_far` warnings; put the listed windows on the consumer's face at the next plan event. Nothing blocks.
6. **Rule 5.** Set `budgets.r_reach_even: true` in the plan; every kit generated from it then re-spaces its bin -> pad chains. A type with its own `chain_even` key keeps that.
7. **Adoption (opt-in, COORD 11-13).** A plan without the keys behaves as before: `r_reach` findings are warnings and kits are unchanged. Each die's first plan event after the freeze (2026-11-15 04:00) sets `budgets.r_reach: "error"` and `budgets.r_reach_even: true` and reaches 0 `r_reach` errors. `reach_homes` (type key) and both budgets are plan schema keys on this branch; a tree without the branch rejects them as unknown keys.

What `share_trunk` builds (rule 1): rings are grouped on a 300-um lattice anchored at the origin home; each group gets one hub relay; one relay trunk runs origin -> hub on a macro-free corridor; each ring keeps its own last stage (its RSTREP copies). Equal stage prefixes are ONE kept relay (`clock_landings.reader_start_owners`), so the origin drives one relay per trunk. Depth is uniform per type; short trunks dwell at the origin home. Absent `share_trunk` = byte-identical RTL.

### Affected types per die

Final checker, KV on main plan vN2i, the others on their wave plans (QC s28, HEAD rp18r2w, S81 h2_2249). Types with at least one finding:

| Die | Soft types | Rule 1 | (no reader chain) | Rule 2 | Rule 4 (pins) | Any error | Rule 3 warn | After `fix --rules 1,4` |
|---|---|---|---|---|---|---|---|---|
| KV | 54 | 42 | 27 | 2 (kv3_sys_c, kv3_hub_C) | 42 (1,338) | 52 | 6 | 52 changed, 0 not fixed, 0 errors left in rules 1 and 4 |
| QC | 120 | 45 | 6 | 0 | 99 (534), 2 of them with no tap in reach | 106 | 28 | 105 changed; 2 types keep errors: coll_core (START sites and taps), coll_ft__cla4a25d77 (no tap in reach) |
| HEAD | 26 | 2 | 1 | 0 | 2 (10) | 3 | 5 | 3 changed, 0 errors left |
| S81 | 394 | 0 (no START pin form) | 0 | 24 (dsdv_slice 20, serdes 3, bk_sel 1) | 14 (49) | 38 | 34 (25 leaf types) | 14 changed, 0 errors left in rule 4 |

Hand items the script reports and does not fix: QC `coll_core` (START sites; a core-filled type) and QC `coll_ft__cla4a25d77` plus `coll_core` (forwarded outputs with no tap within 405 um: add a tap or move the pin); the rule-2 types above (declare `reach_homes`).

### Proof kits

Both kits are private builds through ot-run, renders viewed by RULES-REACH-1.

1. **S81 `ot_s81sl_leaf__t21`** (epyc9 `/srv/opentallas-scratch2/claude/rules-reach-1/s81/t21`): the wave kit a3 (event 7073a6b4a59), re-placed with main's FT-LANE `face_flops.tcl` (train 36) and the rule-5 hook. PLACED, AUTO-GEOM in `after/`. `OT_FT_LANE` 0 station hops over 405 um (max 359); `OT_CHAIN_EVEN` moved 104 chains. Captures over 405 um: 1,134 -> 1,039; worst 700 -> 701 um (flat); relay_collapse 380 -> 327; the bin -> pad class 104 (max 587 um) -> 15 (max 452 um; those chains span over 810 um and need one more pad cycle). AUTO-GEOM still FAILs on classes this rule does not own: about 840 captures are leaf glue registers 410-563 um apart (`g_u_vp_driver_q*` at the vp cores (730, 646) -> `g_u_vp_cf` / `yrow_d` at the ln cores (955-1008, 869); `g_u_vp_driver_lo_d` (918, 811) -> the first leafup_o0 station (535, 964), 536 um). For S81-FORMS-1: this is rule 3 on the leaf form. Put the first leafup_o0 station on the driver's side (or add one station), and keep the vp driver / cf pair on one side of vn_a. Two earlier guard variants were placed and measured (a1: 1,034 captures but one fan-out pad bit pushed 700 -> 827 um; a2: 1,077); the branch tip has the third. Place density render viewed: no new hotspot.
2. **KV `kv3_hub_Eo`** (epyc7 `/srv/opentallas-scratch2/claude/rules-reach-1/kv`): main plan vN2i + `fix --rules 1` on kv3_hub_Eo / kv3_hub_Wo. Plan: reader depth 9 / 8, writer depth 9 / 10; the origin start drives 3 relays (was 58 rings), start_d 11 (was 65 face flops). Strict bind: RC 0, 160 partitions, 2,545 crossings, 0 errors. Bound RTL of hub_Eo: 149 reader relays (522 unshared), 118 writer relays, 0 rings on `cland_start`. PLACED (`kv/pilots_rr1/items/kv3_hub_Eo`), GRT probe 0 overflow. Captures over 405 um: 3,869 (wave kit, BAD) -> 721. **The START fan class is gone: 3,236 -> 0.** `OT_FT_LANE` 0 station hops over 405 um. AUTO-GEOM still FAILs (r2r max 2,376 um) on five classes this fix did not touch:

   | Left over | Captures | Max um | Owner / rule |
   |---|---|---|---|
   | `u_seq` core logic -> `u_bout` output face flops | 321 | 1,086 | rule 3: the seq windows sit far from the seq logic; move the windows or add stations |
   | ring read-select -> `u_bin` eq flop | 179 | 1,283 | CLAND-RING-LOCALITY (bin at the ring) |
   | `u_lpad` r -> q | 68 | 672 | rule 5 gap: these pads are fed by a ring, not a bin, so the default chain head misses them; DIE-KV-100: add `chain_even` chains with head `u_cland_.*` for the hub types |
   | raw reset relay `u_rrl_150` / `u_rrl_100` -> FSTART face flops, bins | 81 | 2,376 | the raw step (`kv_start_corridor_event.py raw`, needs the bound RTL); not run in this proof |
   | other (bin -> first station, misc) | 72 | 1,447 | rule 3 / station sites |

   Place density render viewed: sparse (fill 0.03), a 40-70% cloud at the E centre between the two astk cores, relay streaks across the middle; no START-fan comet. Not routed: the raw-reset class (2.4 mm on a synchronous reset) would fail timing, so the route waits for the raw step in DIE-KV-100's event.

### Limits (what this rule does not do)

- Rule 1 covers the START fan (strap / START-tree origins with a `cland_tstart_in` pin). A root origin (KV kv3_hub_C) and the S81 landing form are out of its scope. Ring -> bin distance and the raw-reset branches stay with their owners (CLAND-RING-LOCALITY, the raw step).
- Rule 2 needs `reach_homes` from the die owner; the script cannot guess where soft logic belongs. Its station fix is tested at plan and G0 level, not yet through a bind.
- Rule 3 prices only buses that name a consumer (buses[].leaf or the core_conns sidecar). HBM was not run (parked).
- Rule 5 moves only the bin -> pad chains (head `u_bin_*`); pads fed straight from a ring (KV hub) need a per-type `chain_even` entry. Other unsited glue registers (S81 leaf `g_u_vp_driver_* -> cf / yrow`, 450-563 um) are not covered; see the S81 proof.

## R-CAP (RULES-CAP-1): partition size, cell cap, outline sizing
Written 2026-11-13 03:57 PST by RULES-CAP-1. Status: rule final; code on branch `claude/rules-cap-1`@daf4c190d3 (parent main fbfb4fc6a6), READY posted to COORD-REVIEW-QUEUE, not yet merged. Evidence: 376 kit runs harvested from the fleet logs (S81 132, QC 76, HBM 57, HEAD 34, KV 33, 44 core kits; 10-28..11-13; epyc2/4/7/8/9, intel1/2), 295 distinct type forms kept as `tools/die_plan/testdata/cap_runs_1113.json`. Outcome labels come from `autopilot/kit_wave_stages.tsv` and `structural.tsv`. I ran no new build. Runs on epyc5/6 and pruned run dirs are not in the sample.

**What the cap measures.** Not memory, and not global placement.
- Memory follows outline area: peak RSS was at most 43 GB for every run up to 4 mm2; HBM q_mcb_ne (10.2 mm2, 765k tap cells, 189k logic) died in GRT at 110 GB. Fit over 100 runs: GB = 4.4 + 3.4 per mm2 + 0.034 per 1,000 instances.
- Global placement took at most 3.4 h, even at 1.4 M instances.
- The wall is the serial timing repair after placement, and it scales with MOVABLE cells (all standard cells except TAPCELL/ENDCAP/FILLER/DECAP; macros apart):

| movable cells after place resize | runs | finished CTS | finished GRT | routed | signed off | hours when it got there |
|---|---|---|---|---|---|---|
| under 100k | 123 | 85 | 59 | 52 | 23 | GRT 0.4, route 0.8 (medians) |
| 100-200k | 85 | 41 | 14 | 12 | 5 | GRT 3.0, route 1.8 |
| 200-300k | 74 | 41 | 3 | 2 | 0 | GRT 3.7, route 5.1 |
| 300-400k | 36 | 13 | 5 | 4 | 0 | GRT 4.5, route 3.0; all four routed at setup -146..-281 ps |
| 400-500k | 33 | 10 | 0 | 0 | 0 | one GRT ran 40 h without finishing |
| over 500k | 25 | 13 | 0 | 0 | 0 | CTS 3-5 h; 16 of 17 KV kv3_pv runs then failed FF hold at -306..-731 ps |

  "Finished" counts are lower bounds: many runs were cancelled or held for a visual verdict, so a low count below 300k is mostly churn, not a limit. Above 400k the count is zero in 58 runs, and that is the limit. The largest sign-off in the sample is 134k movable; the 10-23 record (517k standard cells, 8.8 h route) counted taps too.

**Why counts inflate after synthesis.**
- Tap and endcap cells: ORFS asap7 puts a tap every 50 um in each 0.27 um row (distance 25, staggered) plus 2 endcaps per row = 74k fixed cells per mm2 of free core. Model/measured = 0.994 median on 90 macro-free types. A partition tile runs at 1-4 % standard-cell utilization (median 2.8 %), so taps outnumber logic in most types: S81 leaf 88k taps for 20-170k logic, HBM SU 150-170k. They are fixed, so they cost memory only.
- Place buffering: median x1.41 of the synthesized count for types over 100k (p90 x2.11). One buffer per signal pin (measured 1.00), then repeaters on long nets. The repeater count follows pins x outline size and macro count x outline size, not logic: `place = synth + pins + 0.395 x pins x hp/100 + 58.8 x macros x hp/100`, hp = (W + H)/2 in um. CTS then adds 2.1 %, GRT repair 5.8 % (medians; hold repair can add far more).

**R-CAP-1 budget, per type, on movable cells.**

| stage | budget | enforced by |
|---|---|---|
| synth (pre-floorplan) | 280k, design target | none; the projection below is the gate |
| place (after 3_4 resize) | 400k, HARD | G0C `cell_budget`, kit preflight, pre-floorplan projection, place census |
| CTS | 420k | census line (advisory) |
| GRT after repair | 460k | census line (advisory) |
| any NEW type or split part | 250k after resize | G0C / preflight verdict TARGET, and the split text |

Tap, endcap and filler cells never count. The kit-level raise to 517k (`--native-cell-cap`, COORD 11-04) is for capacity probes only; a sign-off kit does not use it.

**R-CAP-2 outline and utilization.**
- A hard core (its own outline) is sized to 0.30-0.50 standard-cell utilization of its free area after resize, never above 0.55. Signed cores in the sample sit at 0.24-0.50; the one at 0.62 (467k) failed.
- A partition tile keeps the outline the die plan gives it (core-shape freeze). Its utilization is not a target. What it must satisfy is R-CAP-1 on the projection, which already charges the outline: each 100 um of half perimeter costs 0.4 buffers per pin and 59 per macro.
- Memory request per run: `ot-run --mem` = 1.5 x the fit above, at least 32 GB (`cap_estimate.py` prints it). An outline over 6.5 mm2 gets a warning: 6.1 mm2 passed GRT at 42 GB, 10.2 mm2 did not at 110 GB.
- Tap pitch stays at the ORFS asap7 default. Changing it would cut fixed cells only, which are not the limit.

**R-CAP-3 when and how to split.** A type whose projected or measured movable count after resize is over 400k is split before it is built again. No density, effort or retry setting replaces the split.
1. Parts: the smallest n with count x 1.03 / n <= 250k (the 3 % is boundary registers).
2. Where: at lane-group boundaries. Each cut bus is registered at the boundary: one station on the cut links, +1 cycle on those lanes (pre-approved), recorded as latency rows under R-RTL-6.
3. Logic with no lane groups (control, glue, a single engine) is hardened into cores of at most 250k cells at R-CAP-2 utilization, so only glue stays movable in the parent. Core shapes are then frozen.
4. A whole family is split in ONE plan event, with the same cut on every member.
5. A type between 320k and 400k projected (NEAR, inside the +-25 % error band) may launch; the place census stops it if it measures over 400k.

**Implementation** (branch `claude/rules-cap-1`, files under `tools/die_plan/`):
- `cap_estimate.py`: budgets, tap model, projection, split text. `--kit KIT`, `--plan die_plan.json`, `--validate RUNS.json`.
- `check.py`: G0C check `cell_budget` per type (ERROR with `--completeness`, WARN in plain G0). A cored type whose only estimate is a flat table (KV kv3_pv: 7.0 M flat, 0.28-0.44 M really placed) is left to the kit checks.
- `kit_preflight.py`: check `cell_budget` fails an OVER kit before any allocation. The synth count is an earlier attempt's `native_cell_count.json`, a staged `cap_budget.json`, or the plan estimate with `--plan-dir`. With none, the next check judges.
- `native_cell_cap.tcl`: the same projection on the synthesized top, before floorplan repair starts; over 400k stops the run with the split and writes `cap_projection.json`.
- `cell_census.tcl`: the place census (in `pre_cts.tcl`) stops a run measured over 400k before CTS. `OT_CELL_BUDGET_GATE=0` for capacity probes.
- Kits already generated keep their own copies; the checks act on kits generated from main after the merge. No running job is touched (freeze to 11-15 04:00 respected).

**Proof** (`test_cap_estimate.py`, `cap_estimate.py --validate`): predicted against measured post-resize movable count on the 295 distinct runs.
- 222 runs of 100k cells or more: median error 9.9 %, p90 30 %. Hold-out half: 10.1 % / 27.9 %.
- 53 runs measured over 400k: 46 predicted OVER, 7 NEAR (launch with the census stop armed), 0 missed.
- 8 predicted OVER measured under 400k: six at 364-387k (QC st_b, hc1; routed, none signed), plus S81 serdes__t3 and HBM q_spu0.
- Known limit: the model cannot see a placement blow-up. S81 dsdv_slice_*_C forms t1/t6 measured 0.87-1.43 M from 320-390k synthesized, because the second place repair pass inserted 230-740k buffers (R-REACH / R-FLOW). They are still caught, since the projection is already over 400k, but the measured count there is not a guide to the number of parts.

**Types over the rule** (measured after 3_4 resize unless marked; HBM is parked and listed last for the resume):
- S81, split needed: dsdv_slice_*_C family, 16 plan types (c1x t1,t3-t10, c3x t1, iq, kv512, lepe_mu, lepe_nh_mus, lepw_mu, lepw_mus). Synthesized 321-387k with 41-47 macros, projected 440-500k, measured 468k (t10) to 1.43 M (iq t1). Split 2 ways (iq 3 ways) at the lane groups, one event for the family. c3x t1 and five others have no run; they are the same class.
- S81, NEAR (may launch, census armed): ot_s81sl_kv_leaf t1-t5 (measured 287-360k), serdes t4/t13/t15/t16 (324-377k; their failures are R-RTL reach, not count), ot_s81sl_leaf__t47 (326k from 153k synthesized: reach).
- S81, stale estimates: `cells_est.json` gives gunit__t1 484k and eng__t1 429k; eng__t1 measured 105k synthesized, 140k placed. Refresh the table; no split.
- HEAD: none measured over (largest hd_ctl 166k). hd_lep0N has no run and a plan estimate of 365k (projected 444k): the pre-floorplan projection decides at its first build. hd_tile's 1.07 M plan figure is a flat count; it measured 68k synthesized.
- QC, split needed: sle_ctl (measured 419-451k, 20,362 pins) 2 ways; sle/slw_st_a_v1 and _v2, 4 types (421-441k, synthesized 381-397k) 2 ways.
- QC, NEAR: sle/slw_st_b_v1/_v2 (354-380k), sle/slw_hc0-hc2 (353-387k). Inside the budget; the four that routed took 9-10 h and missed setup by 146-281 ps, which is R-RTL / R-CLOCK work. If st_a is cut, cut st_b the same way in the same event.
- KV, split needed: kv3_pv family, 10 plan types (pv, v1-v8, v12; 20 cores each). Measured 423-724k movable from 281-445k synthesized soft logic; 16 of 17 runs failed FF hold after 3-5 h of CTS. pv and v8 2 ways, the rest 3 ways, or harden the soft logic between the 20 cores into cores. kv3_hub_Wo / kv3_hub_Eo (464k / 407k) 2 ways.
- HBM (parked): q_su00 757k, q_su00 pv1 627k, q_su20 pv1 633k, q_su11/pv1 446-468k, q_su31/pv1 393-428k, q_su20 413k, q_su30 396-440k, q_b002/pv1 445-778k, q_b012 762k, q_spu0 407k. The approved pEv12 split (su00 3 ways, others 2) matches R-CAP-3.
## R-FLOW (RULES-FLOW-1): ORFS flow settings for slew, DRV and early buffering
Written 2026-11-13 04:40 PST by RULES-FLOW-1. Status: rule set final for slew/DRV, fanout, max wire, hold and routing; code on branch `claude/rules-flow-1-1113` (epyc7 `/srv/opentallas-scratch2/claude/rules-flow-1/wt`, parent main 055e36edab), not pushed yet. Proof 1 of 3 (HEAD) is done; the S81 and QC proof builds are running, and one knob (GPL_KEEP_OVERFLOW) is decided by them. Their rows are added here when they finish. No KV kit was built: no routed KV kit survives on the fleet to compare against.

**What a flow setting fixes, and what it does not.** Counts are autopilot `structural.tsv` rows since 11-06, HBM excluded.

| failure class | rows | fixed by a flow setting? | owner |
|---|---|---|---|
| GRT overflow | 293 | no: streets and channels | R-STREET |
| "post-CTS hold" | 121 | no: 84 are the GRT setup gate (depth or reach), 36 the FF structural hold gate | R-RTL, R-REACH, R-CLOCK |
| routed, not signed off | 90 | partly: 89 of 90 carry a max-slew failure, and that part is a setting. 67 also fail setup and 89 fail hold, which are not | R-FLOW for slew; R-RTL, R-CLOCK for the rest |
| flow error | 105 | no: kit staging, DPL-0033 (14), DRT-0073 no access point (about 20), tap capacity (10) | tooling, R-STREET |
| DRT-0255 on M8-grant kits | 4 (HEAD rp18) | yes, already merged: no resistance-aware layer assignment on a kit with an M8 grant | HEAD-ROUTE-1, kept here |

What the slew fix is worth alone, from the 29 routed S81, HEAD and QC kits whose sign-off logs survive on the fleet (all not signed off):
- 7 fail max slew only (HEAD hd_spn_wshim_rx, hd_spn_wshim_tx, hd_turn_a; S81 slice_station t24, t30 `cl1653104c`, t45, t7 `cl503f4913`). The setting alone takes them to LOCAL_PASS_NEEDS_PARENT.
- 4 fail max slew plus FF hold on at most 35 endpoints by at most 13 ps (QC coll_ftm, HEAD hd_st_str, S81 t30 x2). With slew clean they enter the existing late-ECO window (30 ps, 100 endpoints, 20 slew nets).
- 7 fail max slew plus FF hold on 409 to 4,236 endpoints, and 3 fail hold alone on 160 to 312 endpoints: R-CLOCK.
- 8 fail setup by 11 to 258 ps as well: R-RTL or R-REACH. The setting removes their slew failure and nothing else.

**Cause, measured** (sign-off `sta.log` and `6_final.v` of 40 routed kits; driver cell and fanout of every violating pin on 7 of them):
- 85 to 99 % of the routed TT max-slew pins sit on a few dozen nets with 17 to 154 loads: clock-landing ring select and write-enable nets, each driven by one BUFx2 to BUFx6f or INVx1 to INVx4. hd_turn_b: 1,399 of 1,408 pins on 39 nets. The rest are long fanout-1 wires (hd_ctl: 441 pins, worst 678 ps).
- No violating pin is a clock pin, in any kit. CTS already uses BUFx24 for root and sinks, with clusters of 23 to 42 sinks.
- `repair_design` repairs to exactly the 320 ps limit on the estimate: worst slew slack after the GRT repair is within -0.33 to +0.29 of the limit, mostly 0.00 to 0.19. Sign-off on routed RCX then reads -0.10 to -1.44. Two things widen the gap: the GRT repair step runs on FF libraries only (`run_kit.sh`: `grt CORNER=BC CORNERS=bc`), while slew signs off at TT; and the estimate is optimistic on wide nets and on long M2/M3 segments (FLOW-RC-1, 10-27).
- The three S81 kits that already carried SLEW_MARGIN 50 (t14, t22, t44) routed with 0 slew pins, at +0.04 to +0.25 slack. The margin was a per-type argument on 4 S81 types; HEAD and KV had neither a margin nor a wire limit.

**R-FLOW-1 design-rule margins.** Every gen_phys type kit repairs to half the slew limit and 80 % of the cap limit: `SLEW_MARGIN = 50`, `CAP_MARGIN = 20`, at the place repair and at the post-GRT repair. This is the rule that clears the class: alone it took hd_turn_b from 1,408 pins to 0.

**R-FLOW-2 fanout.** The place repair limits every driver to 32 loads: `OT_PLACE_MAX_FANOUT = 32` (was off, or 64 from the gen environment). Alone it took hd_turn_b from 1,408 pins to 31. It does not replace R-RTL-2: a net with more than 64 loads at synthesis is still an RTL item. The limit only stops the tool from hanging 64 to 154 loads on one buffer.

**R-FLOW-3 wire length.** The post-GRT repair limits a driven segment to 120 um: `OT_MAXWIRE_UM = 120`. A smaller value given by the die (S81 `--max-wire-um 100`) wins. Do not go below 100: at 50 um the S81 t21 repair inserted 27,000 to 30,000 repeaters on 15,000 to 17,000 nets (14 % of its cells), and the tool warns that a limit under 143 um adds wire delay.

**R-FLOW-4 CTS: no change.** Smaller sink clusters and a stronger leaf buffer were proposed (EXPERT-REVIEW-1). The measurement does not support them: 0 clock pins among the violators, and the leaf buffer is already the largest in the library.

**R-FLOW-5 hold repair: once, at the FF GRT step, target 0, with a budget line.** No hold repair after CTS: it would run on placement RC and be redone at GRT. No repair margin either. A +30 ps repair target was built on hd_turn_b: hold cells went from 631 to 3,323 (18.5 % of the logic cells) and TT setup from +100 to -45 ps on 463 endpoints, because the FF-only repair cannot see TT setup. The routed hold loss (22 to 26 ps on hd_turn_b) is closed by R-CLOCK's two-scene pre-GRT repair, not by a margin here. Each kit now prints `OT_HOLD_BUDGET added N logic_cells M pct P budget 10 ... OK|OVER`. OVER (more than 10 % of the placed logic cells) is a structural hold class for R-CLOCK; nobody raises a cap or a margin for it. The tool cap stays at 100 % as a guard.

**R-FLOW-6 routing.** `ENABLE_RESISTANCE_AWARE = 0` on a kit with an M8 grant, and only there (HEAD-ROUTE-1, merged). hd_turn_b routes clean with it under this rule set (DRC 0), and its slew failure is gone, so the open question in HEAD-ROUTE-1's handoff (did RA=0 cause the 1,408 pins?) is answered: no.

**R-FLOW-7 place-stage buffering (open until proofs 2 and 3).** Timing-driven global placement keeps the repair buffers of its first pass, made at overflow 0.41 to 0.63: +18 to +51 % area on S81 station kits (+371 % on HBM q_su30 pv1, HBM-FORMS-1). The second pass at overflow 0.19 deletes and re-inserts them, so the final count is the same; the first pass only disturbs the placement. `GPL_KEEP_OVERFLOW = 0.25` makes the first pass virtual. On hd_turn_b it changed nothing that matters (same slew result with and without the other rules). It goes into the default only if the S81 and QC builds show no loss; otherwise it stays an opt-in for the HBM resume.

**What is not a setting.** Setup misses of 80 ps and more, hold on hundreds of endpoints, GRT overflow, and nets over 64 loads at synthesis stay with their owners above. `OT_RFLOW=0` in the gen environment writes the old kit; it is for A/B runs only.

**Implementation** (branch `claude/rules-flow-1-1113`, under `tools/die_plan/`):
- `gen_phys.py`: `RFLOW` table and `rflow_margins`, `rflow_max_wire_um`, `rflow_cfg`; `place_max_fanout` defaults to 32. Explicit `--slew-margin`, `--cap-margin`, `--max-wire-um` and a gen-environment `OT_PLACE_MAX_FANOUT` still win, so HBM keeps its 35/35 until its owner drops the argument.
- `hold_repair_pre.tcl`: the `OT_HOLD_BUDGET` line (report only).
- Tests: `test_rflow_defaults.py` (new), `test_place_fanout_cap.py`, `tools/autopilot/test_gp_noconverge_gate.py`.
- No `kit_wave.json` change is needed and no running job is touched. Kits generated from main after the merge get the set; a kit already generated keeps its config.

**Proof 1, HEAD hd_turn_b** (M8-grant kit with a landing ring; copy of HEAD-ROUTE-1's proof kit; epyc7 `/srv/opentallas-scratch2/claude/rules-flow-1/ab/`; every arm has synthesized netlist sha1 `ed0f30376e1c`; private ot-run builds through route, finish and sign-off):

| arm | TT slew pins (worst) | TT setup | FF hold, internal pairs | cells | wire |
|---|---|---|---|---|---|
| old settings, rerun (`turn_b_old`) | 1,408 (424 ps) | +100.36 | -26.35 on 47 | 31,190 | 203.4 mm |
| margins only (`tb_A_margins`) | 0 | +101.38 | -10.53 on 19 | 31,272 | 203.7 mm |
| fanout 32 only (`tb_B_fanout`) | 31 (393 ps) | +103.02 | -12.78 on 15 | 31,390 | 205.0 mm |
| max wire 120 only (`tb_D_maxwire`) | 1,342 (355 ps) | +101.96 | -25.92 on 47 | 31,223 | 203.4 mm |
| GPL keep 0.25 only (`tb_C_gplkeep`) | 1,486 (373 ps) | +33.99 | -19.43 on 45 | 31,211 | 203.7 mm |
| R-FLOW-1/2/3 + GPL keep (`turn_b_v2`) | 0 (283 ps worst routed) | +100.52 | -24.27 on 32 | 31,453 (+0.8 %) | 204.8 mm (+0.7 %) |
| the same + 30 ps hold target (`turn_b`), rejected | 0 | -45.09 on 463 | +1.90 | 34,112 | 208.7 mm |

The rerun of the old settings reproduces the 11-12 proof kit to the digit, so the arms differ by settings only. All arms: DRC 0, antenna 0. Verdict of the new arm: the drv check passes; NOT SIGNED on the 32 hold endpoints, which is HOLD-TAP-1's class (their proof on this kit reaches FF hold +2.71). The +34 ps setup in the GPL-keep-only arm is one landing-origin broadcast path with 40 repeaters and hold pads; it does not appear when the margins are on.

**Proof 2, S81 slice_station__t21, and proof 3, QC coll_ftc**: running on epyc7, old and new arms from the same kit copy. Old sign-offs: t21 135 slew pins and FF hold -17.34 on 409; coll_ftc 2,280 slew pins, setup -90.92 on 49, FF hold -16.48 on 347.

**Dies and types it touches.** Every gen_phys type kit on S81, HEAD, QC and KV, and HBM when it resumes. Hard-core kits from other generators are not changed.
