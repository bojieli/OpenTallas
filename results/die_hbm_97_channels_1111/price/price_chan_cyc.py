"""DIE-HBM-97/HBM-TAPS 11-11: S2 (TOK-13d DS-native) price of the two +1 pin-cycle cores, same model and harness as
tools/token_pass/hbm_price_d44t.py (base 576702.4178 asserted).  Reference = A1 row + the folded compiler_core_delta
S2 extras of plan_p11t (SU +4, IDX +2, SFU +4, COLL_XING +1); new = reference + SU +1 (lane_exp_x inputs, max lane leg,
bound = expected) + IDX +1 (s3_q inputs, serial IDX chain).  Separately each.  ESTIMATE, DO_NOT_COUNT.
Run at a full repo root: PYTHONPATH=src python3 price_taps_cyc.py OUT.json"""
import sys, json
sys.path[:0] = ['tools', 'tools/throughput', 'tools/token_pass']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
res = AC.ROOT / 'results/arch/hgi_sim_20261010/g25_proof'
d, recs = DT.load(res / 'ds_rank0_program.json'); recs = T.rebuild_waits(recs)
rg = {}
for x in json.loads((res / 'ds_full.json').read_text())['results']:
    for s_ in x.get('row_gather') or []: rg[x['layer']] = s_
DT.apply_dyn_counts(recs, rg); cf = DT.NativeCost(d['ops'], recs, row_gather=rg)
CROSS2 = ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST")
def cross(r): return 2 if r.op in CROSS2 else 1
REDUCE_OPS = CROSS2 + ("TOPK_MERGE", "ARGMAX_MERGE")
def is_sfu(r): return r.unit == "SU" and isinstance(r.sut, dict) and r.sut.get("sfu", 0) != 0
TN = {"HC_PRE_NORM": 48, "HC_POST": 32}
def run(ab=True, extra=None, south=0, sfu=0, tnode=False):
    def g(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if r.unit == "COLL" and ab:
            t += 34 * cross(r) + (32 if r.op in REDUCE_OPS else 17) * cross(r)
        if r.unit == "COLL": t += (south * cross(r) if south != "exact" else (10 if cross(r) == 1 else 17))
        if extra: t += extra.get(r.unit, 0)
        if is_sfu(r): t += sfu
        if tnode and r.unit == "FUSED": t += TN.get(r.op, 0)
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']
base = run(ab=False)
assert abs(base - 576702.4178) < 0.1, base
from collections import Counter
units = Counter(r.unit for r in recs)
tok = lambda t: round(1906 * base / t, 2)
def sfu(tap, lane): return 2 * (tap - 2) + 2 * (lane - 2)
REF = {"SU": 3 + 4, "IDX": 38 + 2, "SM": 1, "COLL": 0 + 1, "FUSED": 0}
SFU = sfu(42, 46) + 4
CASES = {"ref_p11t_taps_cyc": {"SU": 1, "IDX": 1}, "chan_SM+1": {"SU": 1, "IDX": 1, "SM": 1}, "chan_SU+2": {"SU": 3, "IDX": 1}, "chan_both": {"SU": 3, "IDX": 1, "SM": 1}}
out = dict(basis=__doc__, base_cycles=base, records_per_unit=dict(units), rows=[])
ref = None
for name, dd in CASES.items():
    e = {k: REF[k] + dd.get(k, 0) for k in REF}
    t = run(extra=e, south="exact", sfu=SFU, tnode=True)
    ref = ref or t
    row = dict(case=name, delta=dd, extra=e, sfu=SFU, cycles=round(t, 2), tok_s=tok(t), d_cycles_vs_ref=round(t - ref, 2),
               pct_vs_ref=round(100 * (ref / t - 1), 4))
    out["rows"].append(row); print(json.dumps(row), flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
