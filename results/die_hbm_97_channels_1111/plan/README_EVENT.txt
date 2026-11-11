DIE-HBM-97/HBM-TAPS hbm-taps-cycles-1111 HBM plan event (11-11), base plan_p11t_ftres_pgr 8955a4efd635 (ftres + PGR). DO_NOT_COUNT.
COORD 11-10 21:01 RULING (3): per-core early taps from lanes/DIE-RECHECK-TAPS.tsv + pin cycles on su_pg_lane_exp_x / hidx_s3_q.
1) Taps: mk_plan_taps_cyc.py -> core-tap insertion_ps / insertion_ff_ps / insertion_basis on 34 core modules (836 taps) +
   q_mca type clock.insertion_ps/ff (335.7/259.6), measured values only (32 SIGNED views, 2 NEAR-CLOSE: q2nf_rest kit_bd2,
   lane1p L1P-HS).  vsN4 keeps form C 380.  Listed, not set: q3bc body_ctl (454 > T/2, Rule A guard), smh_static_front_w
   (SF-SPLIT W half has no plan tap).  die_plan.json diff = clock keys only (eq_gate_taps.json EQ_BY_CONSTRUCTION, 56 types).
2) Pin cycles: +1 input relay stage after the face flop (kit --face-in-stage, event core_kit_args) on
   ot_hbm_su_pg_lane_exp_x_core (51 buses / 1663 bits) and ot_hidx_s3_q (cw thr ties in_line, 636 bits);
   corelat/cycles_hbmtaps_1111.tsv; compiler_core_delta.json pending_not_folded[hbm-taps-cycles-1111].
   EQ: shell-level sat-tempinduct, cycle-shifted (signed shell + input delay == new shell), negative controls in_short and
   no-delay both FAIL (eq_cycles.json).  S2 price: SU +1 / IDX +1 = +1086 cycles, -0.164 %, 1662.80 -> 1660.07 tok/s.
Tools: GitHub claude/die-hbm-97-taps-cyc-1111 results/die_hbm_97_taps_1111/ (on claude/die-hbm-97-ftres-fix-1111 d54b96cc27).

== hbm-channels-1111 rev 2 (HBM-CHANNELS, DO_NOT_COUNT; input to the 12:00 combined HBM compose, not a standalone event) ==
Plan: die_plan.json 85df1184ecea45080cd79da7941ee5464f32c54f83fa436262429af471c46b79.
  This replaces rev 1 fd512301. Rev 2 changes only the station regs_um on q_su11 L8302mx1 and q_su11__physical_v1 L8302x1.
  Cycles and everything else are unchanged.
Base: plan_p11t_taps_cyc 29333b2b.
Replay: replay_chan.sh BASE_DIR OUT_DIR REPO [BOUND_RTL_DIR]
  -> mk_chan_event.py, then ccd_pending.py, then core_conns_batch.py (trace), then cc_merge.py (merge with the base sidecar).
  The replay reproduces every file of this dir except the added check files listed below.

Sections:
 A  SU-CHAN, on q_su11 / q_su11__physical_v1 (69.12 um streets) and q_su01 / q_su01__physical_v1 (120.96 um).
    - The cores move by a uniform lattice shift: one x shift per column and one y shift per row, all multiples of 8.64 um.
    - Clock and reset taps are re-sited.
    - Stations are re-derived by the b2n generator rule (HOP 360, REACH 405).
    - Intent sheet: intent/INTENT_SU_CHAN.md, with 4 SVGs and intent_su_chan.json.
      Row membership, left-to-right order and the exp l/s abutment (gap 0) are all kept.
 B  b types q_b000 / q_b011 and their pv1.
    - All W-strip internal stations moved into the E street, with register counts kept: 72=72 and 192=192.
    - Straightened: q_b011 L51x4. Neighbour q_b002 L51x5 in_window moves [796.608, 908.16] -> [629.376, 740.928].
 C  kv_line (u_sm_front_kv, q_sm0..3).
    - Outline 734.4x233.28 -> 734.4x388.8; origin y 2004.48 -> 1848.96. Only the south edge moves.
    - Pins file: cores/ot_hbm_sm_kv_line__734.4x388.8__kvs1111.json.
    - clock_entries: +155.52 local y, so the die point is unchanged.
 D  q_mcb -> q_mcb_ne (NE_mcb) and q_mcb_nw (NW_mcb). Each is json-equal to q_mcb apart from module and note.
 E  root u_tkm_SW_root reset_from_master.source now cites the part-19 pfdh32 extraction. Note only.

Cycles (contract; NOT EQ by construction). These are the same as rev 1:
 - L5090 48->50 and L5091 47->48: lane fixed_cycles 3->5 and 3->4 (q_su01__physical_v1 internal stations).
 - L8301m, L8302, L8302m, L8314, L8314m: +1 each (one more ft station each in q_su11 / q_su11pv1).
 - Recorded in compiler_core_delta.json pending_not_folded[hbm-channels-cycles-1111], with the HBM-TAPS price:
   expected +0, 1648.00 tok/s; bound 1642.88 tok/s (-0.311%).
 - Stage-equivalence proof: eq_stations.json, verdict ALL_EQ_CYCLE_SHIFTED, from tool eq_stations.py.
   - Per link: OLD is the base station chain taken verbatim from the strict base bind RTL (bind_p11t_taps_cyc_vK5d_c12),
     after checking that the generator pattern reproduces those lines. NEW is the generator chain with the new count.
   - PASS: NEW == OLD followed by k delay stages (data plain flop, eq bit async-reset flop), proved with a yosys
     miter and sat -tempinduct.
   - Two negative controls, which must FAIL: k-1 delay stages, and data bit 0 bypassing the last added stage.
   - All 7 links pass with both controls failing:

     | Type | Link | Stations | Width | k |
     |---|---|---|---|---|
     | q_su11 | L8301mx1 | 6->7 | 1615 | +1 |
     | q_su11 | L8302mx1 | 6->7 | 1615 | +1 |
     | q_su11 | L8314mx1 | 7->8 | 15 | +1 |
     | q_su11pv1 | L8302x1 | 6->7 | 1615 | +1 |
     | q_su11pv1 | L8314x1 | 7->8 | 15 | +1 |
     | q_su01pv1 | L5090_o | 3->5 | 21 | +2 |
     | q_su01pv1 | L5091_o | 3->4 | 41 | +1 |

   - Lane check: on all 7 lanes, the latency delta equals the ft station delta plus the fixed_cycles delta.

core_conns.json:
 - core_conns_batch.py traces the bound RTL of the strict base bind. That trace wires only 281/2553 cores, because cores
   behind split hierarchies trace as {}.
 - cc_merge.py then builds the sidecar per core: the traced entry when it has wiring, otherwise the base entry with refs
   that are invalid in this plan dropped. Result: 281 traced, 2161 base, 111 empty, 1452 stale refs dropped, 0 stale
   refs left. Files: core_conns.json.merge_receipt.json, core_conns.traced.json.
 - Rev 1 used the trace alone. That dropped real wiring and made route_supply worse on q_b112__physical_v1 (0.778 -> 1.18).
   This was a model artifact, not a re-pairing: the plan event does not touch q_b112. With the merged sidecar the
   value is 0.778 -> 0.778.

Checks:
 - eq_gate_channels.json: EQ_BY_CONSTRUCTION_EXCEPT_CONTRACT, 0 non-position paths.
 - g0_channels_report.json and g0diff_channels.json: G0 errors 639 -> 627.
   - Errors gone: hops 5 (L8302 843 um and L8302m 843 um among them) and stations 8.
   - Errors new: hops 1, "lane L8008: ... NW_su00.L8008x6 ... 737 um". This is not a new error. check_hops prints one
     message per lane with the worst hop. The base L8008 message named NW_su11.L8008x2 at 742 um. The base also already
     had the type-slot errors q_su00__physical_v1 L8008x6 737 um and q_b113 L8008x5 712 um, and both stay unchanged.
     This event fixed the su11pv1 slot, so the lane message now names the next pre-existing worst slot.
   - A strict whole-lane L8008 variant could not clear q_su11pv1 L8008x2 within 10 stations (hops 436/444 > 405).
     The su00pv1 and b113 slots are outside this event's types, so L8008 stays as a pre-existing lane error and is
     not offered here.
 - Hop check on the L8302 lanes (rev 2):
   - L8302 hops [1, 182, 179, 164, 337, 346, 333, 356], first 317.
   - L8302m hops [1, 169, 166, 276, 337, 350, 333, 266], first 304.
   - Both are <= 405. Rev 1 had hop 3 at 482 and 477.
 - route_supply, same tool on both arms (base plan with the base sidecar, against this plan with the merged sidecar):
   26 types better and 2 worse.
   - Better: q_su11 4.72->2.01, q_su11pv1 4.64->2.19, q_su01 2.18->1.93, q_su01pv1 2.65->1.01, q_b000 9.01->4.15,
     q_b000pv1 7.40->3.97, q_b010 15.32->11.75, q_b011 6.08->5.50, and 18 more.
   - Worse: NE_io 1.40->1.79. NE_io is unchanged in the plan; this is the sidecar, where u_ep_N2 now has its traced
     entry. Also root 7.74->7.84.
   - Files: route_supply_base_oldcc.tsv and route_supply_chan_merged.tsv.
