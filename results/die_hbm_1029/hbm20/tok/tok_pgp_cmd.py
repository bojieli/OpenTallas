"""DIE-HBM-20: price the HBM-034 qcore drop cost (pgp(q1).command -> sucore q0: +10 NE / +7 NW stations = cycles)
with the SAME ds S2 schedule model as DIE-HBM-10 tok_rerun_c22.py (accepted_cost g25 rank0, NativeCost, T.schedule).
BOUND form: every SU record pays the worst +10 cycles serially (no overlap) -- the command bus is a per-record SU
programme command path in the worst reading; a per-programme reading would be ~0.  Run at repo root."""
import sys, json
sys.path[:0] = ['tools', 'tools/throughput']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
res = AC.ROOT / 'results/arch/hgi_sim_20261010/g25_proof'
d, recs = DT.load(res / 'ds_rank0_program.json'); recs = T.rebuild_waits(recs)
rg = {}
for x in json.loads((res / 'ds_full.json').read_text())['results']:
    for s_ in x.get('row_gather') or []: rg[x['layer']] = s_
DT.apply_dyn_counts(recs, rg); cf = DT.NativeCost(d['ops'], recs, row_gather=rg)
def run(add):
    def g(r, dyn, L):
        c = cf(r, dyn, L); return (c[0] + add.get(r.unit, 0), c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']
from collections import Counter
nsu = Counter(r.unit for r in recs)
base = run({})
out = dict(basis=__doc__, records_per_unit=dict(nsu), base_cycles=base, rows=[])
for name, add in [("SU +7 (NW)", {"SU": 7}), ("SU +10 (NE, bound)", {"SU": 10})]:
    t = run(add); r = dict(case=name, cycles=t, cost_pct=round(100 * (t / base - 1), 3), tok_s_from_1906=round(1906 / (t / base), 1))
    out["rows"].append(r); print(r, flush=True)
print("records", dict(nsu), "base", base)
json.dump(out, open(sys.argv[1], "w"), indent=1)
