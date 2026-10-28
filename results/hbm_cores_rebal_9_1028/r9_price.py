#!/usr/bin/env python3
"""HBM-CORES-REBAL-9 tok/s from the current model (UNCHECKED model, not a measurement): the REBAL-8 d4g_2ring_qbg
priced_layers schedule (tools/hbm_b2/q3stageb/price_su31_calendar.py baseline, results/hbm_cores_rebal_8_1028/price),
with the per-record cost of the lane build MLAT 5 + WCOPY 1 taken from the compiler itself: prod_compile.py's own
schedule of every production SU.VOP record at --mlat 5 --wcopy 1 vs as built (pc_sweep.json, results dir), as the
worst delta of each record class (serial upper bound; the schedule decides what is exposed):
  light SU record           -> max delta over the lane records without ci_sfu (6 edges; REBAL-8 assumed 5)
  SFU record, sut.sfu label -> the measured delta of the matching function (exp/sigmoid/SiLU/div 13-14, rsqrt 14,
                               sqrt(softplus) 78 = side-pipe spacing 19 -> 37 per element); an unmatched label takes
                               the worst lane-SFU delta.
usage: r9_price.py REPO PC_SWEEP_JSON"""
import collections, json, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sw = json.loads(Path(sys.argv[2]).read_text())
sys.path.insert(0, str(root / 'tools'))
from hgi_sim import d4g_quadrant_1017 as Q  # noqa: E402
from hgi_sim import plan_study_price_1017 as PS  # noqa: E402
from hgi_sim import ds_die_split as S  # noqa: E402
from hgi_sim import ds_relay_latency as RL  # noqa: E402
from hgi_sim import ds_mtp_verify as V  # noqa: E402
from hgi_sim import timing as T  # noqa: E402


def worst(case, pred):
    v = [r['delta'][case] for r in sw.values() if r.get('delta') and r['delta'][case] is not None and pred(r)]
    return max(v)


D = {}
for case in ('m4w1', 'm5w0', 'm5w1'):
    D[case] = dict(light=worst(case, lambda r: r['ci_sfu'] == 0 and r['cp_m1'] not in (4, 5)),
                   lane_sfu=worst(case, lambda r: r['ci_sfu'] in (1, 4, 5) or r['cp_m1'] in (4, 5)),
                   rsqrt=worst(case, lambda r: r['ci_sfu'] == 2),
                   spsqrt=worst(case, lambda r: r['ci_sfu'] == 6))


def sfu_kind(r):
    s = str((getattr(r, 'sut', None) or {}).get('sfu', '')).lower() if r.unit == 'SU' else str(r.op).lower()
    if s.isdigit():                    # sut.sfu = the lane ci_sfu code (su_lane_build SFU_*)
        return {2: 'rsqrt', 6: 'spsqrt'}.get(int(s), 'lane_sfu')   # 7 (Engram gate, no record measured) -> worst lane SFU
    if 'softplus' in s or 'spsqrt' in s or 'sp_sqrt' in s:
        return 'spsqrt'
    if 'rsqrt' in s or 'rms' in s:
        return 'rsqrt'
    return 'lane_sfu'


st = json.loads((root / 'results/arch/hbm_plan_study_1017/stages.json').read_text())
st['plan_b_bd'] = Q.bd_stages(st)
led = Q.load_ledger()
kn = dict(Q.knob(Q.ADDERS, st, ledger=led), rings=2, ag_qbg=True)
Q._D4G.clear(); Q._D4G.update(kn)
S.set_variant(PS.VARIANTS['b'], st)
prog = RL.compile_case('AR')
end = [r for r in prog if r.unit == 'CTL' and r.op == 'END'][:1]
segments = [(k, V.rebuild(seg + end)) for k, seg in V.segments(prog)]
costs = V.cost_fn(None)
labels = collections.Counter()
for _, seg in segments:
    for r in seg:
        if Q.su_exec(r) and Q.sfu_using(r):
            labels[(str((getattr(r, 'sut', None) or {}).get('sfu', r.op)), sfu_kind(r))] += 1
T.footprint = V._footprint
res = {}
try:
    for label in ('baseline', 'm4w1', 'm5w0', 'm5w1'):
        tot = 0.0
        d = D.get(label)

        def cf(r, dyn, L):
            c, g, h = costs(r, dyn, L)
            if d and Q.su_exec(r):
                return c + (d[sfu_kind(r)] if Q.sfu_using(r) else d['light']), g, h
            return c, g, h
        for k, seg in segments:
            tot += T.schedule(seg, V.DT.POS, 'S2', cost_fn=cf)['total_cycles']
        res[label] = dict(cycles=tot, tok_s=Q.CLK / tot)
finally:
    T.footprint = V._FP
b = res['baseline']['cycles']
for v in res.values():
    v['added_cycles'] = v['cycles'] - b
    v['loss_pct'] = round(100 * (1 - b / v['cycles']), 4)
print(json.dumps(dict(model='d4g_2ring_qbg priced_layers AR (REBAL-8 r8_price.py baseline), UNCHECKED model',
                      class_deltas=D, sfu_labels={f'{a}|{k}': n for (a, k), n in sorted(labels.items())},
                      AR=res), indent=1))
