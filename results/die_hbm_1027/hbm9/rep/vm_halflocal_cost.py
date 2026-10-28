"""DIE-HBM-9 ESTIMATE: ds S2 tok/s cost of HALF-LOCAL VM bank allocation (each hub half's banks serve only that half's
clients; a tensor is owned by ONE half, the producer's; a consumer in the other half reads it through a one-owner
fixed-latency crossing read across the hub x-bisection; COORD 08:2x prefers this over double writes).
The S2 timing model has no VM bank geometry, so the change is priced per record on top of the unchanged cost fn:
  far_bits = f x (VM input bits of the record); f = 0.5 (row-split producers -> half the words live in the far half)
  extra    = Lx (crossing-read latency, cycles) + far_bits / Wx (crossing-read link width, bits/cycle)
  cons: c + extra   (serial)        opt: max(c, far_bits/Wx) + Lx   (read streams under the op)
Scopes: 'sm'   = only SM matvec input vectors (x is split by halves, every SM needs all of x); unit work in SU/FUSED/IDX/HC
                 is lane-parallel per half copy (local), reductions (SU red) pay Lx once for the scalar exchange;
        'all'  = every record's VM inputs are half far (blanket upper bound).
Usage (repo root): vm_halflocal_cost.py out.json"""
import sys,json,itertools
sys.path[:0]=['tools','tools/throughput']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
res=AC.ROOT/'results/arch/hgi_sim_20261010/g25_proof'
d,recs=DT.load(res/'ds_rank0_program.json');recs=T.rebuild_waits(recs)
rg={}
for x in json.loads((res/'ds_full.json').read_text())['results']:
  for s_ in x.get('row_gather') or []: rg[x['layer']]=s_
DT.apply_dyn_counts(recs,rg);cf=DT.NativeCost(d['ops'],recs,row_gather=rg)
def vm_in_bits(r,dyn,L):
  b=0
  for k,ds in r.desc.items():
    if k=="O" or ds is None or ds.space!="VM": continue
    _,n,m,_,_=T.eff(ds,dyn,L); b+=n*m*4*8
  return b
stat={}
def run(scope=None,Lx=0,Wx=1,mode="cons",f=0.5):
  acc=[0,0.0]
  def g(r,dyn,L):
    c=cf(r,dyn,L)
    if scope is None: return c
    red=r.unit=="SU" and getattr(r,"sut",None) and r.sut.get("red")
    if scope=="sm" and r.unit!="SM":
      return (c[0]+Lx,c[1],c[2]) if red else c
    fb=f*vm_in_bits(r,dyn,L)
    if fb<=0: return c
    acc[0]+=1;acc[1]+=fb
    t=c[0]+Lx+fb/Wx if mode=="cons" else max(c[0],fb/Wx)+Lx
    return (t,c[1],c[2])
  tot=T.schedule(recs,DT.POS,'S2',cost_fn=g)['total_cycles']
  return tot,acc
base,_=run()
out={"basis":"ds S2 (accepted_cost g25 rank0 4120 rec), unchanged cost fn + per-record crossing-read term; ESTIMATE, model UNCHECKED","base_cycles":base,"rows":[]}
for scope,Lx,Wx,mode in itertools.product(("sm","all"),(4,8),(2048,4096),("opt","cons")):
  t,acc=run(scope,Lx,Wx,mode)
  row=dict(scope=scope,Lx=Lx,Wx=Wx,mode=mode,records=acc[0],far_Mbit=round(acc[1]/1e6,2),cost_pct=round(100*(t/base-1),2))
  out["rows"].append(row);print(row,flush=True)
json.dump(out,open(sys.argv[1],"w"),indent=1)
