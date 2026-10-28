"""DIE-HBM-8: per-record / per-op link-bound check for option B (2:1 on hub links of SU,SM,IDX,HC,FUSED).
Link widths W_u (bits/cycle, per direction) = sum of the B-eligible hub station bits (NW hub, c20j plan) whose
endpoint unit is u (unit->VM side = out, VM side->unit = in). Per record: bits_in = sum of input descriptors
n*m*esz*8 (VM word = 4 B), bits_out = O descriptor. S = max(bits_in/W_in, bits_out/W_out) cycles of full-width
link occupancy. rho = S/c. Under 2:1 the record costs c + S + 1 (conservative: the extra stream time is serial)
or max(c, 2S) + 1 (optimistic: streaming overlaps). Usage (repo root): b_perop.py plan.json duty.json out.json"""
import sys,json,collections,math
sys.path[:0]=['tools','tools/throughput']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
plan,dutyf,outf=sys.argv[1:4]
P=json.load(open(plan));D=json.load(open(dutyf))
UNIT=[("hb_coll","COLL"),("hcollg","COLL"),("cij","COLL"),("cxij","COLL"),("cxrc","SU"),("sucore","SU"),("pgp","SU"),("sfu","SU"),
      ("svg","SM"),("smw","SM"),("xl_","SM"),("xq_","SM"),("wbk","SM"),("dbk","DMA"),("hb_idx","IDX"),("mu_","FUSED"),("quant","FUSED"),
      ("hc_","HC"),("vmb","VM"),("vmks","VM"),("vmdel","VM"),("vms","VM"),("vmfc","VM"),("calendar","VM"),("ctl_Q","VM")]
def unit(n):
  if n.startswith("face bus"): return "FACE"
  for k,u in UNIT:
    if k in n: return u
  return "UNK"
def duty(u): return D["unit_duty_vm_aggregate"] if u=="VM" else D["unit_duty"].get(u,1.0)
BU=("SU","SM","IDX","HC","FUSED")
W={tn:collections.defaultdict(float) for tn in ("q_hub_nw","q_hub_ne")}
for tn in W:
  for s in P["partition_types"][tn]["internal_stations"]:
    a,b=unit(s["launch"]),unit(s["capture"]);k=s.get("serial_k") or 1
    uu=[x for x in (a,b) if x!="FACE"];un=max(uu,key=duty);d=max(duty(x) for x in uu)*k
    if not(d<=0.5 and un in BU): continue
    # direction relative to the unit: bits leaving the unit = out, entering = in; per-cycle width = bits/serial_k
    if a==un and b!=un: W[tn][(un,"out")]+=s["bits"]/k
    elif b==un and a!=un: W[tn][(un,"in")]+=s["bits"]/k
    else: W[tn][(un,"int")]+=s["bits"]/k
Wn=W["q_hub_nw"]
res=AC.ROOT/'results/arch/hgi_sim_20261010/g25_proof'
d,recs=DT.load(res/'ds_rank0_program.json');recs=T.rebuild_waits(recs)
rg={}
for x in json.loads((res/'ds_full.json').read_text())['results']:
  for s_ in x.get('row_gather') or []: rg[x['layer']]=s_
DT.apply_dyn_counts(recs,rg);cf=DT.NativeCost(d['ops'],recs,row_gather=rg)
def bits(r,dyn,L):
  bi=bo=0
  for k,ds in r.desc.items():
    if ds is None or ds.space=="NONE": continue
    _,n,m,_,_=T.eff(ds,dyn,L);es=4 if ds.space=="VM" else T.ESZ[ds.fmt]
    if k=="O": bo+=n*m*es*8
    else: bi+=n*m*es*8
  return bi,bo
info={}
def S_of(r,dyn,L):
  # the unit's in-link carries what the unit reads (VM side -> unit = "in"), out-link what it writes
  bi,bo=bits(r,dyn,L);u=r.unit
  wi=Wn.get((u,"in"),0);wo=Wn.get((u,"out"),0)
  s=max(bi/wi if wi else 0.0, bo/wo if wo else 0.0)
  return s,bi,bo
def run(units=(),mode=None):
  def g(r,dyn,L):
    c=cf(r,dyn,L)
    if r.unit in units:
      s,bi,bo=S_of(r,dyn,L)
      if mode=="cap": info[id(r)]=(r.unit,r.src_key,r.op,c[0],s,bi,bo)
      if mode=="cons": return (c[0]+s+1,c[1],c[2])
      if mode=="opt": return (max(c[0],2*s)+1,c[1],c[2])
    return c
  return T.schedule(recs,DT.POS,'S2',cost_fn=g)['total_cycles']
base=run()
run(BU,"cap")
per_unit=collections.defaultdict(lambda:[0.0,0.0,0,0]);per_op=collections.defaultdict(lambda:[0.0,0.0,0,""])
for u,sk,op,c,s,bi,bo in info.values():
  pu=per_unit[u];pu[0]+=c;pu[1]+=s;pu[2]+=1;pu[3]+=(s>0.5*c)
  po=per_op[(u,sk)];po[0]+=c;po[1]+=s;po[2]+=1;po[3]=op
out={"basis":"ds S2 schedule (accepted_cost, g25 rank0 4120 rec); NW-hub B-eligible station widths; ESTIMATE",
     "base_cycles":base,"W_bits_per_cycle":{f"{u}.{dr}":round(v) for (u,dr),v in sorted(Wn.items())},
     "W_ne":{f"{u}.{dr}":round(v) for (u,dr),v in sorted(W["q_hub_ne"].items())},
     "per_unit":{u:dict(cycles=round(v[0]),stream=round(v[1]),rho=round(v[1]/v[0],3) if v[0] else 0,records=v[2],records_link_bound=v[3]) for u,v in per_unit.items()},
     "ops_link_bound_top40":sorted([dict(unit=u,op=sk,kind=v[3],cycles=round(v[0]),stream=round(v[1]),rho=round(v[1]/v[0],3),records=v[2]) for (u,sk),v in per_op.items() if v[1]>0.5*v[0]],key=lambda x:-x["cycles"])[:40],
     "ops_total":len(per_op),
     "ops_by_unit":{u:dict(ops=sum(1 for (uu,_) in per_op if uu==u),link_bound=sum(1 for (uu,_),v in per_op.items() if uu==u and v[1]>0.5*v[0]),
                         cycles_link_bound=round(sum(v[0] for (uu,_),v in per_op.items() if uu==u and v[1]>0.5*v[0]))) for u in BU},
     "ops_link_bound_not_SM":[dict(unit=u,op=sk,kind=v[3],cycles=round(v[0]),stream=round(v[1]),rho=round(v[1]/v[0],3)) for (u,sk),v in per_op.items() if u!="SM" and v[1]>0.5*v[0]],
     "rho_hist_by_unit":{u:dict(collections.Counter(min(10,int(10*v[1]/v[0])) /10 for (uu,_),v in per_op.items() if uu==u and v[0]>0)) for u in BU},"ops_link_bound_n":sum(v[1]>0.5*v[0] for v in per_op.values())}
cost={}
sets={"full":BU,"SU":("SU",),"SM":("SM",),"IDX":("IDX",),"HC":("HC",),"FUSED":("FUSED",),"cheap":("IDX","HC","FUSED"),
      "no_SM":("SU","IDX","HC","FUSED")}
for nm,us in sets.items():
  for mode in ("cons","opt"):
    t=run(us,mode);cost[f"{nm}.{mode}"]=round(100*(t/base-1),2)
out["tok_s_cost_pct"]=cost
json.dump(out,open(outf,"w"),indent=1);print(json.dumps({k:out[k] for k in ("W_bits_per_cycle","per_unit","tok_s_cost_pct","ops_link_bound_n","ops_total","ops_by_unit","ops_link_bound_not_SM")},indent=1))
