"""Pin-cycle S2 bounds, 2026-11-05. Run from a FULL OpenTallas tree with PYTHONPATH=src.
Sparse results/rtl changes NativeCost fallback: asserted base and reference refuse that.
These are model bounds; no G5 token or selected-view adoption claim.
EXPX+5 charged to all SU records is conservative; WBQ charged once per KVWB or COLL.
"""
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
CROSS2 = ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST")
def cross(r): return 2 if r.op in CROSS2 else 1
REDUCE_OPS = CROSS2 + ("TOPK_MERGE", "ARGMAX_MERGE")
def is_sfu(r): return r.unit == "SU" and isinstance(r.sut, dict) and r.sut.get("sfu", 0) != 0
TN = {"HC_PRE_NORM": 48, "HC_POST": 32}
def run(ab=True, extra=None, south=0, sfu=0, tnode=False, opx=None, hc=None):
    def g(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if r.unit == "COLL" and ab:
            t += 34 * cross(r) + (32 if r.op in REDUCE_OPS else 17) * cross(r)
        if r.unit == "COLL": t += (south * cross(r) if south != "exact" else (10 if cross(r) == 1 else 17))
        if extra: t += extra.get(r.unit, 0)
        if is_sfu(r): t += sfu
        if opx and r.unit == "FUSED": t += opx.get(r.op, opx.get("*", 0))
        if tnode and r.unit == "FUSED": t += TN.get(r.op, 0)
        if hc and r.unit == "HC": t += hc.get(r.op, 0)
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']
base = run(ab=False)
assert abs(base - 576702.4178) < 0.1, base
rec = run(extra={"IDX": 31, "SU": 3})
assert abs(rec - 610734.931155155) < 0.1, rec
tok = lambda t: round(1906 * base / t, 2)
def sfu(tap, lane): return 2 * (tap - 2) + 2 * (lane - 2)
A1 = dict(extra={"IDX": 38, "SM": 1}, sfu=sfu(42, 46))
from collections import Counter
print("HC ops", dict(Counter(r.op for r in recs if r.unit=="HC")), flush=True)
X0={")[0])
X0={"SU":3,"IDX":38+2,"SM":1+1,"COLL":4,"FUSED":4}; S0=A1["sfu"]+2
EXPS=(1,4,5)
FO={"HC_PRE_NORM":8,"HC_POST":4}
def price(topk=0, sfux=0, kvwb=0, fence=0, idx=0, su=2, fu=0, cx=0, dx=0, cl=0, sfa=0):
    e=dict(X0)
    for k,v in {"IDX":18+idx,"SM":7,"SU":su,"FUSED":fu,"COLL":cl}.items(): e[k]=e.get(k,0)+v
    def g(r,dyn,L):
        c=cf(r,dyn,L); t=c[0]
        if r.unit=="COLL":
            t+=34*cross(r)+(32 if r.op in REDUCE_OPS else 17)*cross(r)
            t+=(10 if cross(r)==1 else 17)+cx*cross(r)
        t+=e.get(r.unit,0)
        if is_sfu(r):
            t+=S0+11+sfa
            if r.sut["sfu"] in EXPS: t+=sfux
        if r.unit=="FUSED": t+=FO.get(r.op,0)+TN.get(r.op,0)
        if r.unit=="DMA": t+=dx
        if r.unit=="HC": t+={"HC_MIX_POST":84}.get(r.op,0)
        if r.unit=="COLL" and r.op=="TOPK_MERGE": t+=topk
        if r.unit=="DMA" and r.op=="KVWB_DS": t+=kvwb
        if r.unit=="DMA" and r.op=="FENCE": t+=fence
        return (t,c[1],c[2])
    return T.schedule(recs,DT.POS,"S2",cost_fn=g)["total_cycles"]
b=price(topk=448,sfux=4,idx=9,su=4)
print(json.dumps(dict(case="base",cycles=round(b,1),tok_s=round(1906*base/b,2))),flush=True)

for n,k in [("ev75_reference",dict(sfa=4,idx=11,su=8,cx=1)),("EXPX_vB_SU_write_plus5_bound",dict(sfa=4,idx=11,su=13,cx=1)),("WBQ_GIN1_KVWB_plus1",dict(sfa=4,idx=11,su=8,cx=1,kvwb=1)),("WBQ_GIN1_all_COLL_plus1_bound",dict(sfa=4,idx=11,su=8,cx=1,cl=1))]:
    t=price(topk=448,sfux=4,**k)
    print(json.dumps(dict(case=n,cycles=round(t,1),tok_s=round(1906*base/t,2),pct=round(100*(b/t-1),3))),flush=True)
