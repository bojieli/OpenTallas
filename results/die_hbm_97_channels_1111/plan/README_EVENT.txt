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

== hbm-channels-1111 (HBM-CHANNELS, DO_NOT_COUNT; input to the 12:00 combined HBM compose, not a standalone event) ==
Plan: die_plan.json fd5123010508864c82549536c8a04b4db9bc826cd60b945384f3f489c9c3e02a.
Base: plan_p11t_taps_cyc 29333b2b.
Replay: replay_chan.sh BASE_DIR OUT_DIR REPO [BOUND_RTL_DIR]
  -> mk_chan_event.py, then ccd_pending.py, then core_conns_batch.py.
  The replay was checked to reproduce this dir byte-for-byte.

Sections:
 A  SU-CHAN, on q_su11 / q_su11__physical_v1 (69.12 um streets) and q_su01 / q_su01__physical_v1 (120.96 um).
    - Lattice-snapped core and content moves; clock and reset taps re-sited.
    - Stations re-derived by the b2n generator rule (HOP 360, REACH 405).
 B  b types q_b000 / q_b011 and their pv1.
    - All W-strip internal stations moved into the E street, with register counts kept: 72=72 and 192=192.
    - Straightened: q_b011 L51x4 (612 b, -167.232 um). Neighbour q_b002 L51x5 in_window moves
      [796.608, 908.16] -> [629.376, 740.928].
 C  kv_line (u_sm_front_kv, q_sm0..3).
    - Outline 734.4x233.28 -> 734.4x388.8; origin y 2004.48 -> 1848.96. Only the south edge moves.
    - Pins file: cores/ot_hbm_sm_kv_line__734.4x388.8__kvs1111.json.
    - clock_entries: +155.52 local y, so the die point is unchanged.
 D  q_mcb -> q_mcb_ne (NE_mcb) and q_mcb_nw (NW_mcb).
    - Each is json-equal to q_mcb apart from module and note.
    - Reason: S_u_refcfg_Q_tgt differs per instance.
 E  root u_tkm_SW_root reset_from_master.source now cites the part-19 pfdh32 extraction. Note only.

Cycles (contract; NOT EQ by construction):
 - L5090 48->50 and L5091 47->48: lane fixed_cycles 3->5 and 3->4 (q_su01__physical_v1 internal stations).
 - L8301m, L8302, L8302m, L8314, L8314m: +1 each (one more ft station each in q_su11 / q_su11pv1).
 - latency_groups unchanged.
 - Recorded as compiler_core_delta.json pending_not_folded[hbm-channels-cycles-1111], with the HBM-TAPS price:
   expected +0, 1648.00 tok/s; bound 1642.88 tok/s (-0.311%).
 - Stage-equivalence proof for the extra stations: MISSING.

core_conns.json:
 - Regenerated with core_conns_batch.py (plan-route-3 7a3db5b6b652), no --base.
 - Source: the bound RTL of the strict base bind die-hbm-97-taps/bind/bind_p11t_taps_cyc_vK5d_c12/rtl.
   The plan event changes no partition wiring names. Ft and internal station counts and core moves do not change bound
   bus or core partners, and q_mcb_ne/nw have no hard cores.
 - 64 types, 281/2553 cores wired; receipt in core_conns.json.receipt.json.
 - Stale refs (bus or core names not in this plan): 0. The previous sidecar had 249 refs in 27 types.

Checks:
 - eq_gate_channels.json: EQ_BY_CONSTRUCTION_EXCEPT_CONTRACT, 0 non-position paths.
 - g0_channels_report.json: G0 errors 639 -> 629.
