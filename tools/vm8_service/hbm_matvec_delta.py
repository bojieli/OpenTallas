import sys, json
"""Fixed edges added to every SM.MATVEC record of the r25gq S2 schedule -> end-to-end tok/s loss (DS and Qwen).
Run from the root of a main checkout:  python3 tools/vm8_service/hbm_matvec_delta.py 14 30 36 52"""
sys.path.insert(0,'tools/throughput')
import accepted_cost as A
import collections
sys.path.insert(0,'tools')
from hgi_sim import timing as T
def sched(model):
    # same construction as accepted_cost.hbm_schedule, with a fixed number of cycles added to one op
    run,count=A.hbm_schedule(model)
    import inspect
    cl=inspect.getclosurevars(run)
    recs,pos,cf=cl.nonlocals['recs'],cl.nonlocals['pos'],cl.nonlocals['cf']
    def rund(op=None,delta=0.0):
        def g(r,dyn,L):
            c=cf(r,dyn,L)
            return (c[0]+delta if f"{r.unit}.{r.op}"==op else c[0]),c[1],c[2]
        return T.schedule(recs,pos,"S2",cost_fn=g)["total_cycles"]
    return rund,count
out={}
deltas=[float(x) for x in sys.argv[1:]]
for wl,model in (('ds_ar','ds'),('qwen_ar','qwen')):
    rund,count=sched(model)
    base=rund()
    out[wl]=dict(base_cycles=round(base,1),sm_matvec_records=count['SM.MATVEC'],rows=[])
    for d in deltas:
        new=rund('SM.MATVEC',d)
        out[wl]['rows'].append(dict(added_edges_per_matvec=d,cycles=round(new,1),added_cycles=round(new-base,1),e2e_loss_pct=round(A.loss_pct(base,new),3)))
print(json.dumps(out,indent=1))
