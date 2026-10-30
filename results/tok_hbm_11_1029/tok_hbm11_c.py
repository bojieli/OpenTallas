"""TOK-HBM-11 (C): price HBM-039 vms_glue_nw_t pipeline option (+1 cycle on the VM ring stop / hub control) -- base: tok_hbm11.py.
TOK-HBM-11: price (A) plan d21h EP_S1 hop lane (+17 cyc each way, root<->vsN0) and (B) HBM-BIND-7 hub collective
q0 drop (+<=12 NE / +<=15 NW cycles per hub-collective hop stage) with the SAME ds S2 schedule model as DIE-HBM-10
tok_rerun_c22.py / DIE-HBM-20 tok_pgp_cmd.py (accepted_cost g25 rank0, NativeCost, T.schedule).  Added cycles go on
COLL records only, serially (no overlap) = BOUND form.
(A) ep_S1 = lane 1 of hb_coll_SW's 2-lane SerDes (die_r18h5: hb_coll_SW.tx_pin_flit[1223:612] -> ep_S1.tx_frame,
    ep_S1.rx_pin_flit -> hb_coll_SW.rx_pin_flit lane 1) = the off-die collective path.  A crossing pays TX +17 on the
    sending die and RX +17 on the receiving die = +34; crossings per record as perf.coll_cycles (2 for
    ALL_REDUCE_SUM / GROUP_REDUCE_MCAST, else 1).  Bound: every COLL record pays 2 crossings.
(B) bound/est: every COLL record walks the hub collective reduce -> body -> ring once per crossing; worst hub (NW) maxima
    reduce +15, body +11, ring +6 = +32 per crossing; bound 3 stages x 15 = +45 per crossing.  Op-aware estimate of
    record: only merge/reduce ops (GROUP_REDUCE_MCAST, TOPK_MERGE, ARGMAX_MERGE) use the reduce stage; gathers pay
    body + ring = +17 per crossing.
Run at repo root: python3 tok_hbm11.py OUT.json"""
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
def run(per_cross=0, fixed_cross=None, extra=None, opaware=None):
    def g(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if r.unit == "COLL":
            t += per_cross * (fixed_cross or cross(r))
            if opaware: t += (opaware[0] if r.op in REDUCE_OPS else opaware[1]) * cross(r)
        if extra: t += extra.get(r.unit, 0)
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']

base = run()
rows = []
# VM-ring users: every record whose operands or results cross the hb_vms hub/ring (SM/SU/FUSED/HC/ATT/IDX/DMA/ARGMAX/COLL)
ALL = {u: 1 for u in ("SM", "SU", "FUSED", "HC", "ATT", "IDX", "DMA", "ARGMAX", "COLL")}
for name, ex in [("C pipeline +1 on SU records (estimate: SU VM round trips)", {"SU": 1}),
                 ("C pipeline +1 on SU+SM records", {"SU": 1, "SM": 1}),
                 ("C pipeline +1 on every non-CTL record (bound)", ALL),
                 ("C pipeline +2 (request+response) on every non-CTL record (bound x2)", {u: 2 for u in ALL})]:
    t = run(extra=ex); r = dict(case=name, cycles=t, cost_pct=round(100 * (t / base - 1), 3), tok_s_from_1906=round(1906 / (t / base), 1))
    rows.append(r); print(r, flush=True)
json.dump(dict(base_cycles=base, rows=rows), open(sys.argv[1], "w"), indent=1)
