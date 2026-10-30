"""DIE-HBM-28-C: price the HBM scorer row-1 feed hop chain (b100 -> b102, 2,777 b, ~11.2 mm after V-R1, ~28 stations
-> ~30 added cycles) + row-1 result return b103 -> b101 (~73 b, adjacent, ~1-2 cycles) on the IDX (index scorer)
records, ON TOP OF the TOK-HBM-11 estimate of record (A+B op-aware: EP_S1 34 x cross + coll q0 drop 32/17 x cross =
5.163 % -> 1812.4 tok/s).  SAME ds S2 schedule model as tok_hbm11.py / DIE-HBM-10 tok_rerun_c22.py (accepted_cost
g25 rank0, NativeCost, T.schedule); IDX cycles added serially per IDX record (the way DIE-HBM-10 added IDX +17).
Run at repo root: PYTHONPATH=src python3 tok_hbm28c.py OUT.json"""
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
out = dict(basis=__doc__, idx_ops=dict(Counter(r.op for r in recs if r.unit == "IDX")),
           records_per_unit=dict(Counter(r.unit for r in recs)), base_cycles=base, ab_cycles=ab,
           ab_cost_pct=round(100 * (ab / base - 1), 3), rows=[])
print("base", base, "A+B", ab, out["ab_cost_pct"], flush=True)
cases = [("IDX +17 alone (DIE-HBM-10 check)", 0, None, 17), ("IDX +30 alone", 0, None, 30),
         ("A+B + IDX +22", 34, (32, 17), 22), ("A+B + IDX +30 (feed chain, ESTIMATE OF RECORD)", 34, (32, 17), 30),
         ("A+B + IDX +32 (feed 30 + result return 2)", 34, (32, 17), 32), ("A+B + IDX +34", 34, (32, 17), 34),
         ("A+B + IDX +60 (bound: feed + return each a full 30-cyc chain)", 34, (32, 17), 60)]
for name, pc, oa, ix in cases:
    t = run(pc, oa, {"IDX": ix})
    r = dict(case=name, idx_add=ix, cycles=t, cost_pct_vs_1906=round(100 * (t / base - 1), 3),
             tok_s=round(1906 / (t / base), 1))
    if pc: r["delta_pct_vs_1812"] = round(100 * (t / ab - 1), 3)
    out["rows"].append(r); print(r, flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
