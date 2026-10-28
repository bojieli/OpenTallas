#!/usr/bin/env python3
"""DIE-HBM-7 hub ESTIMATE (no build): 4x3 regional grid face demand vs 6 pins/um for
 (base) as planned, (A) connectivity re-placement of the hub contents (same outline, same cores; nodes reassigned to
 grid regions by simulated annealing on face load, area/soft-cell capacity kept), (B) 2:1 time-multiplex of links with
 duty <= 50% (duty = unit busy share from the per-token S2 schedule x current serial_k), (A+B) both.
Usage: hub_replace_est.py die_plan.json duty.json out.json [--nx 4 --ny 3 --seed 1 --iters N]"""
import json,sys,math,random,collections,argparse
A=argparse.ArgumentParser();A.add_argument("plan");A.add_argument("duty");A.add_argument("out")
A.add_argument("--nx",type=int,default=4);A.add_argument("--ny",type=int,default=3);A.add_argument("--seed",type=int,default=1)
A.add_argument("--iters",type=int,default=400000);A.add_argument("--hard-util",type=float,default=0.80)
A.add_argument("--soft-cap",type=float,default=360000);A.add_argument("--F",type=float,default=1.3);A.add_argument("--reach",type=float,default=405.0);A.add_argument("--b-units",default="SU,SM,IDX,HC,FUSED,DMA,ATT,ARGMAX,CTL")
a=A.parse_args();P=json.load(open(a.plan));D=json.load(open(a.duty))
UNIT=[("hb_coll","COLL"),("hcollg","COLL"),("cij","COLL"),("cxij","COLL"),("cxrc","SU"),("sucore","SU"),("pgp","SU"),("sfu","SU"),
      ("svg","SM"),("smw","SM"),("xl_","SM"),("xq_","SM"),("wbk","SM"),("dbk","DMA"),("hb_idx","IDX"),("mu_","FUSED"),("quant","FUSED"),
      ("hc_","HC"),("vmb","VM"),("vmks","VM"),("vmdel","VM"),("vms","VM"),("vmfc","VM"),("calendar","VM"),("ctl_Q","VM")]
def unit(n):
  for k,u in UNIT:
    if k in n: return u
  return "UNK"
def duty(u): return D["unit_duty_vm_aggregate"] if u=="VM" else D["unit_duty"].get(u,1.0)
out={"b_units":a.b_units,"scope":"ESTIMATE only, no build, no adoption","plan":a.plan,"grid":f"{a.nx}x{a.ny}","duty_basis":D["basis"],"types":{}}
for tn in ("q_hub_nw","q_hub_ne"):
  t=P["partition_types"][tn];W,H=t["outline_um"];nx,ny=a.nx,a.ny;cw,ch=W/nx,H/ny
  hard=t["hard_cores"];hrect={h["inst"]:(h["origin_um"][0],h["origin_um"][1],h["origin_um"][0]+h["outline_um"][0],h["origin_um"][1]+h["outline_um"][1]) for h in hard}
  hc=set(hrect)
  soft={c["inst"]:c["cells"] for c in t["contents"] if not any(h==c["inst"] or h.startswith(c["inst"]+"_") or h.startswith(c["inst"]+".") for h in hc)}
  def cell(x,y): return (min(nx-1,max(0,int(x/cw))),min(ny-1,max(0,int(y/ch))))
  def resolve(name,pt):
    if name.startswith("face bus"): return ("F",)+cell(*pt)
    for h,r in hrect.items():
      if r[0]-1<=pt[0]<=r[2]+1 and r[1]-1<=pt[1]<=r[3]+1: return ("H",h)
    return ("S",name.split(".")[0])
  edges=collections.Counter();ebits_par={};ekey_unit={};eregs=collections.Counter();pos=collections.defaultdict(list)
  for s in t["internal_stations"]:
    u=resolve(s["launch"],s["from_um"]);v=resolve(s["capture"],s["to_um"])
    pos[u].append(s["from_um"]);pos[v].append(s["to_um"])
    k=s.get("serial_k") or 1
    uu=[unit(x) for x in (s["launch"],s["capture"]) if not x.startswith("face bus")]
    d=max(duty(x) for x in uu)*k
    un=max(uu,key=duty);key=(u,v,d<=0.5 and un in a.b_units.split(","),un)
    edges[key]+=s["bits"]
  nodes=sorted(set(x for e in edges for x in e[:2]),key=str)
  harea={h["inst"]:h["outline_um"][0]*h["outline_um"][1] for h in hard}
  def init_cell(n):
    if n[0]=="F": return n[1:]
    if n[0]=="H": r=hrect[n[1]];return cell((r[0]+r[2])/2,(r[1]+r[3])/2)
    ps=pos[n];return cell(sum(p[0] for p in ps)/len(ps),sum(p[1] for p in ps)/len(ps))
  # hard cores without stations still occupy area
  for h in hc:
    if ("H",h) not in nodes: nodes.append(("H",h))
  def faces(ca,cb):
    (ax,ay),(bx,by)=ca,cb;f=[]
    for x in range(min(ax,bx),max(ax,bx)): f.append(("v",x,ay))
    for y in range(min(ay,by),max(ay,by)): f.append(("h",bx,y))
    return f
  def cap(f): return 6.0*(ch if f[0]=="v" else cw)
  def run(mode,place):
    """mode: base|B; place: dict node->cell -> face loads"""
    L=collections.Counter()
    for (u,v,el,un),b in edges.items():
      bb=b/2 if (mode=="B" and el) else b
      for f in faces(place[u],place[v]): L[f]+=bb
    return L
  def summary(L,place,mode):
    rows=[(f,L[f],cap(f)) for f in L]
    hareas=collections.Counter();scells=collections.Counter()
    for n in nodes:
      c=place[n]
      if n[0]=="H": hareas[c]+=harea[n[1]]
      if n[0]=="S": scells[c]+=soft.get(n[1],0)
    for (u,v,el,un),b in edges.items():
      bb=b/2 if (mode=="B" and el) else b
      cu,cv=place[u],place[v];dist=(abs(cu[0]-cv[0])*cw+abs(cu[1]-cv[1])*ch) or 200.0
      nreg=max(1,math.ceil(dist/a.reach)-1);scells[cu]+=a.F*bb*nreg/2;scells[cv]+=a.F*bb*nreg/2
    tot=sum(L.values())
    return dict(worst_face_ratio=round(max(v/c for _,v,c in rows),2),faces_over=sum(v>c for _,v,c in rows),faces=len(rows),
                max_face_bits=round(max(v for _,v,_ in rows)),total_face_bits=round(tot),total_face_capacity=round(sum(cap(f) for f in all_faces)),
                max_region_hard_util=round(max(hareas.values())/(cw*ch),3),max_region_soft_cells_unbanked=round(max(scells.values())),
                regions_soft_over_cap_unbanked=sum(v>a.soft_cap for v in scells.values()))
  all_faces=[("v",x,y) for x in range(nx-1) for y in range(ny)]+[("h",x,y) for x in range(nx) for y in range(ny-1)]
  base_place={n:init_cell(n) for n in nodes}
  res={}
  res["base"]=summary(run("base",base_place),base_place,"base")
  res["B"]=summary(run("B",base_place),base_place,"B")
  elig=collections.Counter();tot=collections.Counter()
  for (u,v,el,un),b in edges.items(): tot[un]+=b;elig[un]+=b if el else 0
  res["B_eligible_bits_by_unit"]={u:[elig[u],tot[u]] for u in tot}
  # (A) SA re-placement
  for mode in ("base","B"):
    rnd=random.Random(a.seed);place=dict(base_place)
    inc=collections.defaultdict(list)
    for e,b in edges.items():
      bb=b/2 if (mode=="B" and e[2]) else b
      inc[e[0]].append((e,bb));inc[e[1]].append((e,bb))
    L=run(mode,place);hA=collections.Counter()
    for n in nodes:
      if n[0]=="H": hA[place[n]]+=harea[n[1]]
    Acap=a.hard_util*cw*ch;Acap=max(Acap,max(hA.values()))  # never tighter than as-planned
    p=8
    def fcost(f,l): return (l/cap(f))**p
    mov=[n for n in nodes if n[0]!="F" and (n in inc)]
    T0=0.5;best=None
    cost=sum(fcost(f,L[f]) for f in all_faces)
    for it in range(a.iters):
      n=rnd.choice(mov);old=place[n]
      new=(min(nx-1,max(0,old[0]+rnd.choice((-1,0,1)))),min(ny-1,max(0,old[1]+rnd.choice((-1,0,1)))))
      if new==old: continue
      if n[0]=="H" and hA[new]+harea[n[1]]>Acap: continue
      dL=collections.Counter()
      for e,bb in inc[n]:
        u,v=e[0],e[1]
        if u==v: continue
        cu=place[u];cv=place[v]
        for f in faces(cu,cv): dL[f]-=bb
        cu2=new if u==n else cu;cv2=new if v==n else cv
        for f in faces(cu2,cv2): dL[f]+=bb
      dc=sum(fcost(f,L[f]+d)-fcost(f,L[f]) for f,d in dL.items())
      Tk=T0*(1-it/a.iters)+1e-6
      if dc<0 or rnd.random()<math.exp(-dc/(Tk*max(cost,1e-9))):
        for f,d in dL.items(): L[f]+=d
        cost+=dc;place[n]=new
        if n[0]=="H": hA[old]-=harea[n[1]];hA[new]+=harea[n[1]]
    res["A" if mode=="base" else "A+B"]=summary(run(mode,place),place,mode)
    res[("A" if mode=="base" else "A+B")+"_moved_nodes"]=sum(place[n]!=base_place[n] for n in nodes)
  out["types"][tn]=res;print(tn,json.dumps(res))
json.dump(out,open(a.out,"w"),indent=1)
