"""DIE-HBM-30: d29d pgp relay +2 cyc (hub->su01 L0 14 + su01->su00 hop 2 = 16 vs direct L36 14; su00/su01 are
lockstep halves of one SU, so the whole SU command delivery is +2) priced in the token model TOGETHER with the
DIE-HBM-29-T set. pgp_*.command feeds the SU command path -> unit SU, priced as a serial +2 on every SU record
(no masking assumed). su20 relay path L2 6 + 2 = 8 vs L38 9 is not slower (+0).
Base: DIE-HBM-29-T tok_hbm29t.py (same model, same 576702.4 guard). Run at repo root: PYTHONPATH=src python3 tok_hbm30.py OUT.json"""
"""DIE-HBM-29-T: price THREE d28c latency increases TOGETHER vs the TOK-HBM-11 A+B estimate of record (1812.4 tok/s):
 (a) L6/L6m word hub->b100 7->8 (+1): carries hb_idx query (ql_codes/ql_sc/ql_head/key_index) + mu_keybuf key_out
     -> index scorer row-0 = model unit IDX, serial per IDX record (+1).
 (c) scorer row-1 feed hop chain: IDX +30 (DIE-HBM-28-C estimate of record).
 (b) L181/L181m su31->hub 2->5 (+3): carries hc_NW3.c_rr[512]+c_w_done (HC gather lg_rr), SU bank_read_data[512]
     (cxport inject inj_q3) and su_NW3 tap near_rq/near_wq (hub VM banks Q6/Q7).  HC gather and cxport inject are
     masked by the slower q0/q2 round trips (plan lanes L36 14 + L55 8, L38 9 + L59 8 vs L174 2 + L181 5) -> +0;
     the SU tap path is the only un-masked leaf, priced as a BOUND (+3 on every SU record) and a wide bound
     (+3 on SU, COLL, HC, FUSED records).
SAME ds S2 schedule model as tok_hbm28c.py (accepted_cost g25 rank0, NativeCost, T.schedule).
Run at repo root: PYTHONPATH=src python3 tok_hbm29t.py OUT.json"""
import sys, json
sys.path[:0] = ['tools', 'tools/throughput']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
from collections import Counter
res = AC.ROOT / 'results/arch/hgi_sim_20261010/g25_proof'
d, recs = DT.load(res / 'ds_rank0_program.json'); recs = T.rebuild_waits(recs)
rg = {}
for x in json.loads((res / 'ds_full.json').read_text())['results']:
    for s_ in x.get('row_gather') or []: rg[x['layer']] = s_
DT.apply_dyn_counts(recs, rg); cf = DT.NativeCost(d['ops'], recs, row_gather=rg)
CROSS2 = ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST")
def cross(r): return 2 if r.op in CROSS2 else 1
REDUCE_OPS = CROSS2 + ("TOPK_MERGE", "ARGMAX_MERGE")
def run(per_cross=0, opaware=None, extra=None):
    def g(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if r.unit == "COLL":
            t += per_cross * cross(r)
            if opaware: t += (opaware[0] if r.op in REDUCE_OPS else opaware[1]) * cross(r)
        if extra: t += extra.get(r.unit, 0)
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']
base = run()
assert abs(base - 576702.4178) < 0.1, base   # model trap guard (TOK-HBM-11 README)
ab = run(34, (32, 17))
out = dict(basis=__doc__, records_per_unit=dict(Counter(r.unit for r in recs)), base_cycles=base, ab_cycles=ab,
           ab_cost_pct=round(100 * (ab / base - 1), 3), ab_tok_s=round(1906 / (ab / base), 1), rows=[])
print("base", base, "A+B", ab, out["ab_cost_pct"], flush=True)
cases = [("pgp alone: SU +2", {"SU": 2}),
         ("29T plausible + pgp: IDX +31, SU +2 (ESTIMATE OF RECORD)", {"IDX": 31, "SU": 2}),
         ("29T bound + pgp: IDX +31, SU +3+2", {"IDX": 31, "SU": 5}),
         ("29T wide bound + pgp: IDX +31, SU +5, COLL/HC/FUSED +3", {"IDX": 31, "SU": 5, "COLL": 3, "HC": 3, "FUSED": 3})]
for name, ex in cases:
    t = run(34, (32, 17), ex)
    r = dict(case=name, extra=ex, cycles=t, cost_pct_vs_1906=round(100 * (t / base - 1), 3),
             tok_s=round(1906 / (t / base), 1), delta_pct_vs_1812=round(-100 * (1 - ab / t), 3))
    out["rows"].append(r); print(r, flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
