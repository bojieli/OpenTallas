OWN-QWEN/KV-PARENTS 10-18 (tree K.STA.PARK)

qkd_pvw_die_t (die slots pvw_0 = qkd_pvw_s, pvw_1 = qkd_pvw_n): NOT a hardened parent. The frame is 1555.2 x 12009.6 um
(2,501 relay replicas, 404k station flops, ~2,790 leaves): a single hardened tree across 12 mm breaks the landed-regions
standard, so the DIE is its parent (kv_expand frames qkd_pvw_s / qkd_pvw_n; the die's regional trees + landed crossings).
Trial (pvw_expand_trial2.sh on a COPY of kvs14p-fa7fe4ff9, ot-epyc5): kvs14p tools + main c402cb103 kv_expand.py,
qkd_pvw_die_t.sv, qkd_pv_rtrunk.sv and the result-trunk / ctl_t views -> EXPAND rc 0, per pair 2,790 leaves on 8 CLOSED
leaf views, 0 undriven / 0 multi-driven / 0 unbound parent inputs / 0 overlaps / 0 outside slot, NO ctl_t stand-in
(OT_KV_PV_T_CTL_KIT=qkd_pv_ctl_t_d54f58a95: that dir holds the FIRST_INPUT_AGE 96 closure qkd_pv_ctl_t_d54f58a96-
d54f58a96-287098501, record f0be3773d, TT +73.68 / FF +23.00).
Ties (58,533 bits / pair): 48,384 on 892 qkd_rlys_296 and 10,148 on 463 qkd_rlys_36 relay replicas = unused pad bits of
the standard relay widths (input a), and 1 on ctl_t pair_id (identity strap). No functional port tied.
Trial 1 (kvs14p's own tree fa7fe4ff9) FAILED: "qkd_pvw_s: child u_RH_r0 (qkd_pv_rs_hd) has no closed view": the kv-plan5
branch predates b2f0f71cb (native successors qkd_rlyi_258s / qkd_pv_rs_hd_r) and lacks those views.
DIE ACTIONS (KV-PLAN5, die GEN owner): merge main (b2f0f71cb + views), add qkd_pvw_s,qkd_pvw_n to OT_KV_EXPAND, set
OT_KV_PV_T_CTL_KIT=qkd_pv_ctl_t_d54f58a95 and drop OT_KV_PV_T_CTL_STANDIN; ERL 7 (KV-ERTAP): the compiler/pair calendar
takes astk_eread e_after_header (record astk_eread) -- a die calendar item, no pair RTL change.
qkd_pv_rs_hd_r is native FAIL (KV-PAR2 owns it): its re-close is the remaining leaf dependency of the expanded pair.

AD3-KV-PARENTS 10-18 23:50 (successor lane; K.STA.PARK)
BIND TABLE (kvs14p-fa7fe4ff9 port_bind.json, ot-epyc5 /srv/opentallas-scratch/claude/qwen-kvsys/kvs14p-fa7fe4ff9; strict v2
PASS 54 REAL masters / 33,207 inst; GEN = claude/kv-plan5-1018 fa7fe4ff9 with OT_KV_SEQ_STATIC=1, AHUB_STATIC/ASTK_ST default 1):
  qkd_seq_st  -> module qkd_seq_static_s  (1 inst, REAL, 0 unbound; only 'hs' unread)   => qkd_seq_static has 0 instances
  qkd_ectlk   -> module qkd_ectl3_kiss_st (32 inst, REAL, 0 unbound)                    => qkd_ectl3_kiss_s has 0 instances
  qkd_pvw_s / qkd_pvw_n -> module qkd_pvw_die_t (1 + 1 inst, REAL)
Source: tools/qwen_kv_die/kv_static_die.py bindings(): qkd_ectlk = 'qkd_ectl3_kiss_st' if ASTK_ST else 'qkd_ectl3_kiss_s';
qkd_seq_st = qkd_seq_static_s if SEQ_S (same on origin/main, claude/kv-plan5-1018, codex/hkv-die-1018).
SUPERSEDE: qkd_ectl3_kiss_s -> qkd_ectl3_kiss_st (job qkd_ectl3_kiss_st-e4-13455b5bb, COORD-approved 0ix);
           qkd_seq_static  -> qkd_seq_static_s (die-placed, below).

qkd_seq_static_s: NOT a hardened parent (the 10-18 22:10 hardened kit p1 is DROPPED: its --cts gate FAILED -- GPL-0307
divergence on 3,068 tiny pin-hold cells in a 604.8 x 475.2 frame at 18% fill, kst 506-um comb reach core -> W pin, no GRT).
The parent is WIRES-ONLY (9 closed leaves, 0 glue cells: qkd_seq_static_s.sv only instantiates + assigns), not replicated,
so per the top-down contract the die is its parent: kv_expand frame qkd_seq_st (SEQ_S_PLAN, this branch) places
u_core (qkd_seq_core_st_s-c1-62789a1ed, native PASS), 4 x qkd_seq_xs_s (x1-9c9c3d7b5, PASS), 4 x qkd_seq_fan_s
(f1-1d16a0569, PASS) on the 43.2-um lattice inside the seq slot.
TRIAL (seq_expand_trial.sh on a COPY of kvs14p-fa7fe4ff9, ot-epyc5; log seq_expand_trial_kvs14p.log): EXPAND rc 0,
removed 1 / added 9, 0 ties, 0 undriven / 0 multi-driven / 0 unbound parent inputs / 0 overlaps / 0 outside slot.
DIE ACTIONS (HKV-DIE): take kv_expand.py from claude/ownq-kvpar-1018; OT_KV_EXPAND += qkd_seq_st,qkd_pvw_s,qkd_pvw_n;
views physical/ref_tile/{qkd_seq_core_st_s/views/qkd_seq_core_static_s, qkd_seq_xs_s/views/qkd_seq_xs_s,
qkd_seq_fan_s/views/qkd_seq_fan_s} (on main); the seq slot may shrink later (9 leaves = 53k um2 in 287k um2).
PVW remaining leaf: qkd_pv_rs_hd_r native FAIL (capture S + R 259.9 > 190 on 94 pins: a0v 31 / a1v 31 select copies
S 140-151 ps, a0 24 / a1 6 data bits, a0t / a1t; R 108.7, spread 8.5 TT / 8.4 FF; launch 178.1 PASS) -- owner below.
