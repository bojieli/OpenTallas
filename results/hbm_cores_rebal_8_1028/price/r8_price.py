#!/usr/bin/env python3
"""HBM-CORES-REBAL-8 ESTIMATE (UNCHECKED model sensitivity, not an adoption price): token cost of
 (c) SU lane MLAT 4 -> 5 (ot_hdc_fp32_mul_lat5i, input cut): emit->lane write LIN 23+4(MLAT-3)+.. +4 edges;
     SFU chains: exp/sigmoid +7 (D_EXP 7*MLAT), rsqrt +9, softplus +18 (upper bound used for every SFU-using record);
 (b) bank write commit +1 edge (registered per-column write copy) on every SU-executing record.
Same historical d4g_2ring_qbg priced_layers compiler + schedule as tools/hbm_b2/q3stageb/price_su31_calendar.py
(baseline reproduced there); the added edges are applied to every su_exec record of every segment (serial-chain
upper bound: the schedule decides what is exposed)."""
import json, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'tools'))
from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_die_split as S
from hgi_sim import ds_relay_latency as RL
from hgi_sim import ds_mtp_verify as V
from hgi_sim import timing as T
st = json.loads((root / 'results/arch/hbm_plan_study_1017/stages.json').read_text())
st['plan_b_bd'] = Q.bd_stages(st)
led = Q.load_ledger()
kn = dict(Q.knob(Q.ADDERS, st, ledger=led), rings=2, ag_qbg=True)
Q._D4G.clear(); Q._D4G.update(kn)
S.set_variant(PS.VARIANTS['b'], st)
out = {}
for case in ('AR', 'MTP'):
    try:
        prog = RL.compile_case(case)
    except Exception as e:  # noqa
        out[case] = dict(error=repr(e)); continue
    end = [r for r in prog if r.unit == 'CTL' and r.op == 'END'][:1]
    segments = [(k, V.rebuild(seg + end)) for k, seg in V.segments(prog)]
    costs = V.cost_fn(None)
    T.footprint = V._footprint
    res = {}
    try:
        for label, light, sfu in [('baseline', 0, 0), ('b_wcommit_plus1', 1, 1), ('c_mlat5', 4, 4 + 18),
                                  ('b_plus_c', 5, 5 + 18), ('b_plus_c_sfu_exp_only', 5, 5 + 7)]:
            tot, nsu, nsfu = 0.0, 0, 0
            def cf(r, dyn, L):
                c, g, h = costs(r, dyn, L)
                if Q.su_exec(r):
                    return c + (sfu if Q.sfu_using(r) else light), g, h
                return c, g, h
            for k, seg in segments:
                nsu += sum(Q.su_exec(r) for r in seg); nsfu += sum(Q.su_exec(r) and Q.sfu_using(r) for r in seg)
                tot += T.schedule(seg, V.DT.POS, 'S2', cost_fn=cf)['total_cycles']
            res[label] = dict(cycles=tot, tok_s=Q.CLK / tot, su_records=nsu, sfu_records=nsfu)
    finally:
        T.footprint = V._FP
    b = res['baseline']['cycles']
    for v in res.values():
        v['added_cycles'] = v['cycles'] - b; v['loss_pct'] = round(100 * (1 - b / v['cycles']), 4)
    out[case] = res
print(json.dumps(out, indent=1))
