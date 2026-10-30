"""TOK-12 2026-10-30: price HBM plan-cycle deltas on the accepted DS native S2 model (same as TOK-8/9/10 price_ve2.py,
Codex hbm_root_price_1030). Base clean 576702.4178 (assert kept); record R = A+B COLL (34/cross + 32 reduce / 17 other)
+ IDX+31 + SU+3 = 610734.93 cyc = 1799.79 tok/s (d31t record). Each case = record terms + listed per-record serial
extras (BOUND: every record of a unit pays the unit's added latency serially, no overlap credit beyond S2 schedule).
Lane->unit mapping (assumptions, see TOK-12 lane file):
  L28/L28m NW/NE_hub->sm0 data (d38s +1): SM +1 (alt SU +1, DIE-HBM-10 hub-row mapping).
  d38a L36/L36m hub->su00 data +1: SU +1.
  d40h L700/L701 Southern VMS + HCOL words 18/21 vs old 11 (data +7/+10): COLL +7 once / +10 once / pair +17 per cross
       phase (Codex pair17 form; all-COLL exposure = over-exposure bound, Northern L4/L4m stay 11).
  V-A (S0, DIE-HBM-37 va_route_lengths.tsv hop chains, d32q geometry): IDX = L6 +1 + b100->b102 47 + b103->b101 32
       = 80 (replaces record IDX 31); FUSED = hub->b113(ctl) 30 + max ctl<->lane round trip b113<->b112 46+46 = 122.
       wide: + SU +16 (hub<->su00/su20 unplanned 690-776 b at 25 vs planned L38 9) + DMA +13 (hub<->spb0 27 vs 14 direct).
  HBM-LOC-1 L1 (Sa+C2, est_out.txt on d40h): IDX = 1 + 2 + 6 = 9; FUSED = hub->ctl 8 + su31 tap round trip 27+27
       = 62, + b110<->hub kv +12 (L5/L23) = 74; bound + b112<->hub +10 = 84; SU 0 (bound +2: su20 L38/L59 9->11).
Run at repo root: PYTHONPATH=src python3 price_tok12.py OUT.json"""
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
def run(ab=True, extra=None, coll_once=0, coll_percross=0, tnode=False):
    def g(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if r.unit == "COLL" and ab:
            t += 34 * cross(r) + (32 if r.op in REDUCE_OPS else 17) * cross(r)
        if r.unit == "COLL":
            t += coll_once + coll_percross * cross(r)
        if extra: t += extra.get(r.unit, 0)
        if tnode and r.unit == "FUSED": t += {"HC_PRE_NORM": 48, "HC_POST": 32}.get(r.op, 0)
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']
base = run(ab=False)
assert abs(base - 576702.4178) < 0.1, base   # model trap guard (TOK-HBM-11 README)
REC = {"IDX": 31, "SU": 3}
rec = run(extra=REC)
assert abs(rec - 610734.931155155) < 0.1, rec
tok = lambda t: round(1906 * base / t, 2)
out = dict(basis=__doc__, base_cycles=base, record_cycles=rec, record_tok_s=tok(rec),
           records_per_unit=dict(Counter(r.unit for r in recs)), rows=[])
def case(name, extra, once=0, pc=0, tn=False):
    e = dict(REC); e.update(extra)
    t = run(extra=e, coll_once=once, coll_percross=pc, tnode=tn)
    row = dict(case=name, tnode=tn, extra=e, coll_once=once, coll_percross=pc, cycles=round(t, 2), tok_s=tok(t),
               pct_vs_record=round(100 * (rec / t - 1), 3), pct_vs_1812_4=round(100 * (tok(t) / 1812.4 - 1), 3))
    out["rows"].append(row); print(json.dumps(row), flush=True)
# Codex N1 tnode (HC_PRE_NORM +48 / HC_POST +32 on FUSED) composites; reproduce Codex 627009.379 first
case("codex_repro_tnode_pair17", {}, pc=17, tn=True)
case("POR_d40h_L1_core_pair17_tnode", {"SM": 1, "IDX": 9, "FUSED": 74}, pc=17, tn=True)
case("POR_d40h_L1_bound_pair17_tnode", {"SM": 1, "IDX": 9, "FUSED": 84, "SU": 5}, pc=17, tn=True)
case("POR_d40h_L1_core_ne7once_tnode", {"SM": 1, "IDX": 9, "FUSED": 74}, once=7, tn=True)
case("POR_d40h_VA_core_pair17_tnode", {"SM": 1, "IDX": 80, "FUSED": 122}, pc=17, tn=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
