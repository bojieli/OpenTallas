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
