#!/usr/bin/env python3
"""TOKSIM-S81B SMX / LEG element records (10-19). Usage: mk_json.py SMX|LEG BRANCH@COMMIT OUT"""
import json, sys
cls, br, out = sys.argv[1], sys.argv[2], sys.argv[3]
W = '2026-10-19 21:55 PT'
RTL_SMX = dict(module='ot_s81_su_sms (u_sms in every dsdv_svc_rs) -> ot_s81_su_smh / ot_s81_su_smq + ot_dsrom_su_softmax_* / fdiv_f12 / hdc fp leaves',
               source='origin/claude/s81-bind-mu4-1019@19bf4121e', blob='ot_s81_su_sms a26f63f27987, ot_s81_su_smh cf66f44117f2, ot_s81_su_smq d1a15a169dce (all 25 executing files: RELEASE_BLOBS.txt)',
               in_release_source=True)
BENCH = 'rtl/dsrom_sys/s81_dv/su_sm/test/tb_toksim_smx.sv@' + br
EV = 'results/rtl/toksim_s81b_smx_1019/runs/run_flat16_{L0_attend_T128,L2_attend_T640}.log (SMXT + SMX PASS lines); stress0-3 identical cycles; smt16 (hardened-tile views dsfd_su_t_*) pin cycles identical'
JOB = 'ot-run ot-epyc9 build oth-ubuntu-678197-1792462610 (Verilator 5.050), run oth-ubuntu-1057659-1792470390 (21:26)'
GOLD = 'tools/dsrom_su_softmax.reference (hdc_golden_v41 attend softmax + normalise + inverse RoPE) on the 1M token L0 (T 128) / L2 (T 640 = 128 window + 512 selected) real-head operands of su_cases_v2_ildr.pkl, asserted equal to the chain checks by toksim_smx_prep.py; + 4 random 16-head stress cases'
SHAPE = '16 heads (all 16 SM shares lockstep, NH=16; NH=2 identical), T 128 (L0/L1: nv 8 score rows, lt 3) and T 640 (L2-L39: nv 40, lt 6), 32 P.V rows, D 512; every e row (FP32 x16) and o row (BF16 inverse-RoPE half) bit-exact'
SVC = ('in-context cross-check: release 16-slice dsdv_svc_rs bench (TOKSIM-S81/SU exe, +trace) full1m T 640: every slice last SE row -> first e (W) row = 106 '
       '(e.g. slice 0 5331 -> 5437), short300 T 428: 106 -- identical to the standalone se_pin, so no wire stage sits between the slice score assembler and the share (svctr/run_*_s1.log.gz)')
OWED = ('NOT folded: (1) mu4c has no SM target storage (svc_rs SM face w_v/w_a/w_m/w_d/w_st open, LEAD2-S81 INBOX [BIND 17:40]); the SO target '
        'arrives in GEN mu5 (SMWIRE, claude/s81-smwire-1019 e0b7607f3, not release) with priced edges "last SO write -> last XS arrival 115 E / 132 W"; '
        '(2) +3 q words SOT/job (SMWIRE calendar, issue side, not on this op)')
if cls == 'SMX':
    d = 'cycles at the share pins (tb_toksim_smx header), cycle 0 = first score row at the pins, score rows back to back (1 a cycle, the assembler rate); '
    ops = [
     dict(op='attn.max', dag_cls='su', n_crit=40, old_cycles_per_instance=[186.9, 221.6], by_old={'186.9': 28, '221.6': 60},
          definition=d + 'max = first score row -> root max out (u_smh.mv); per instance: L0/L1 (T 128, old 186.9) 28, L2-L39 (T 640, old 221.6) 60 (= nv + 20)'),
     dict(op='attn.exp', dag_cls='su', n_crit=40, old_cycles_per_instance=[236.3, 289.7], by_old={'236.3': 92, '289.7': 124},
          definition=d + 'exp = root max out -> last e row at the pins (incl. se_pin: last score row -> first e row 106); L0/L1 92, L2-L39 124'),
     dict(op='attn.den', dag_cls='su', n_crit=40, old_cycles_per_instance=[72.0, 88.0], by_old={'72.0': 32, '88.0': 32},
          definition=d + 'den = last e row at the pins -> row sum at the root (u_smh c_ov & c_ol); 32 for both shapes'),
     dict(op='attn.sink', dag_cls='su', n_crit=40, old_cycles_per_instance=196.0,
          per_layer=dict({'L0': 29, 'L1': 29}, **{f'L{i}': 44 for i in range(2, 40)}),
          definition=d + 'sink = row sum at the root -> o_den at the pins (exp(sink - max) added, den delivered to the divide engines); L0/L1 (lt 3) 29, L2-L39 (lt 6) 44. Check: max+exp+den+sink = se_chain (first score row -> o_den) 181 / 260, no gap or overlap'),
     dict(op='attn.normalize', dag_cls='su', n_crit=40, old_cycles_per_instance=244.9, cycles=85, tail_priced=132,
          definition='SO job: first P.V row at the share pins -> last o row (BF16, normalise + inverse RoPE) at the pins, 32 P.V rows back to back; 85 for every layer. '
                     'SO parameter rows + 40 cycles cos/sin are issued before the first P.V row (off the path). tail_priced 132 = SMWIRE mu5 priced edges last SO write -> last XS arrival (W, worst) '
                     'so the transport the old node carried in its RET wire is not dropped (priced, not measured; not in release mu4c)'),
    ]
    for o in ops:
        o.update(grade='measured-release-RTL', shape=SHAPE, bit_exact=True, golden=GOLD, rtl=RTL_SMX, bench=BENCH, evidence=EV, job=JOB,
                 edges_owed=OWED, note=('Old DAG numbers were the S58 hub SU chain incl. BCAST 22 / RET 15 wire stages + r8 hub-slab stations per op; on p4l-MU the SM share sits in every regional svc slice. ' + SVC))
    ops.append(dict(op='attn.gather', dag_cls='select', n_crit=8, old_cycles_per_instance=[808.0, 811.0, 819.0], cycles=None, grade='pending', bit_exact=None,
        definition='selected compressed-row gather (top-k ids -> rows held at the owning svc slices)',
        shape='not measured', golden=None, rtl=dict(module='dsdv_svc_rs PCs (HBM row requests) + ROWS frames', source='19bf4121e', blob=None, in_release_source=True),
        bench='rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_rs.sv@19bf4121e (traced)', evidence='svctr/run_full1m_s1.log.gz: RQ (PC row requests) cycles 55..3162, all before GO 5016',
        job='ot-epyc7 oth-ubuntu-2051895-1792462766', edges_owed=None,
        note=('NOT measurable with the existing release bench: the svc_rs bench issues SEL_IDS / ROWS frames host-paced long before the compiled GO and models HBM response latency '
              '(off-chip, modelled), so there is no ids-ready -> last-row-landed interval on the static schedule. Old model number kept (grade stays as committed). '
              'Needs a vehicle that issues SEL_IDS at the compiled cycle after topk_final with the fixed HBM latency (+static_io=1); not built in this short lane.')))
    rec = dict(cls='SMX', written=W, agent_branch=br, ops=ops,
               summary=dict(ar_crit_old=41399.8, ar_crit_new_measured=2*28+38*60+2*92+38*124+40*32+2*29+38*44+40*85, ar_crit_new_incl_tail=2*28+38*60+2*92+38*124+40*32+2*29+38*44+40*(85+132),
                            bench_weakness='tb_toksim_smx compares with != (an X golden compares false): job1 ran with an empty case glob and printed a vacuous PASS nv=0; '
                                           'only runs with nv 8 / 40 and checks = NH x (nv + 32) are used (run2). No mutant witness in this lane.'))
else:
    part = 'on-die leg farthest slice <-> end slice, both ends (p4l plan, 67 cyc an end)'
    RTL = dict(module='ot_s81sl_rstop x16 + 112 ring links (hop-0 ICG, 7 x dsfd_dvrlyh_276 half-cycle relays, dsfd_dvland_276 strap k 4/5) transcribed from GEN mu4c die.v (sha ce6b7913) by gen_chain.py',
               source='origin/claude/s81-bind-mu4-1019@19bf4121e (die base ceaed19c4)', blob='rstop d089448887d5, ot_s81_rly dd70cc2dc04a, rly_masters_dv276 72c17619b1b5, rly_masters_dvh 0567b4082944, ot_s81_land 29d5d8f807c1, dsfd_dvland 3f4a565f9307 (RELEASE_BLOBS.txt)',
               in_release_source=True)
    DEF = ('per crossing = OUT (source stop samples ci_b -> end stop samples ri = xdie issue edge) + IN (end stop loads inward ro = xdie landing edge -> owning stop loads dl_e/dl_w), '
           'farthest slice (7 ring links) at both ends; definitions identical to tb_xdie_s81_2 so the leg adds to the measured xdie co-sim with no gap/overlap. '
           'Circuits: S d.ES->(d+1).WS 132, S (d+1).WS->d.ES 140, N d.EN->(d+2).WN 128, N (d+2).WN->d.EN 138; the record uses the worst (140) on every crossing (which circuit each xdie term rides is not in the base record). '
           'Law: each ring link + the stop it enters = k_link + 5 edges; latency constant over all 128 windows / 6,320 beats, 1 beat a cycle sustained, so payload size adds no cycles')
    terms = [('substage_hop0', 'hop', 1), ('substage_hop1', 'hop', 1), ('unplaced_hops', 'hop', 62), ('head.hop', 'hop', 1), ('attn.a_allgather', 'coll', 1),
             ('ffn.router_allgather', 'coll', 1), ('attn.rows_allgather', 'coll', 1), ('attn.idx.topk_merge', 'coll', 1), ('head.argmax_merge', 'coll', 1),
             ('attn.out_allreduce', 'coll', 2), ('ffn.combine_allreduce', 'coll', 2), ('mtp.hop_in', 'hop', 1), ('wave.h2..h6', 'hop', 1),
             ('E1/E14.rows_allgather, attn.cand.merge', 'coll', 1)]
    ops = []
    for op, c, k in terms:
        ops.append(dict(op=op, dag_cls=c, xdie_part=part, crossings_per_instance=k, old_cycles_per_instance=134.0 * k, cycles=140.0 * k,
                        range_per_instance=[128 * k, 140 * k], grade='measured-release-RTL', definition=DEF,
                        shape='16 rstops, 2 tiers (S/N), W- and E-bound, OUT and IN, every production payload a peer (1/3/8/13/32/40/128/132/321 beats of 128 B) + 1..7-link column sweep: 128 windows, 6,320 beats',
                        bit_exact=True, golden='gen_leg.py stimulus (golden/stim.hex, windows.json): every beat full 1,104-bit compare incl. compiled hops field, in order; + law check parse_leg.py (0 violations)',
                        rtl=RTL, bench='rtl/test/toksim_s81b_leg/tb_leg_s81.sv + leg_chain_gen.sv@' + br,
                        evidence='results/rtl/toksim_s81b_leg_1019/l1/otrun.log "PASS leg_s81: 6320 beats ... bit-exact" + LEG_STATS last_cycle 44694; l1/leg.json per-window latencies',
                        job='ot-run ot-epyc8 oth-ubuntu-410900-1792462807 (Verilator 5.050)',
                        edges_owed='NOT folded: LEAD2-S81 INBOX [SLICE 16:39] ot_s81sl_xg successor rstop RELAY=1 (claude/s81-xgr-1019@5e5845264, not in mu4c): +1 edge per stop = +7 an end, +14 a crossing (worst 154) once bound',
                        note=('fold: replace the base xdie part "' + part + '" of every term of this op (base results/arch/token_path_1018/ds_rom.json, grade priced) by cycles. '
                              'Off-critical / exposed-0 terms stay 0. AR 377 crossings 50,518 -> 52,780 (+2,262); MTP 403 crossings 54,002 -> 56,420 (+2,418). '
                              'Mutants: OT_S81_RLY_MUT bench FAIL (790 mismatches); OT_S81_LAND_MUT_SEL (landing reads one slot early) NOT detected by the bench verdict '
                              '(bits exact, BENCH_PASS, no epoch fault in the zero-delay sim) -- caught only by the law check (128 violations, 63 vs 70 at 7 links). '
                              'Cross-tier owners (V rung, tv* links) not measured.')))
    rec = dict(cls='LEG', written=W, agent_branch=br, ops=ops,
               summary=dict(ar_crossings=377, ar_old=50518, ar_new=52780, mtp_crossings=403, mtp_old=54002, mtp_new=56420,
                            mutants={'rly_mut': 'bench FAIL (detected)', 'land_mut_sel': 'bench PASS = NOT detected by the bench; law check FAIL'}))
json.dump(rec, open(out, 'w'), indent=1)
print(out, len(rec['ops']))
