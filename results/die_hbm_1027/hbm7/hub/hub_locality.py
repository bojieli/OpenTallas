#!/usr/bin/env python3
"""DIE-HBM-7 ESTIMATE (COORD 07:1x, 12.13 rework of the hub contents; no build, no RTL):
(i) core-to-core traffic matrix inside each hub + each core's external clients (die lanes resolved to their end
partition); share of station bits local to one client (SM row / PHY / SU slice / ...), local to one function group,
or die-wide. (ii) slices = cores clustered on their main external client (anchor), unanchored cores follow their
heaviest partner; slices >3 mm span split by function group. (iii) per slice: soft cells vs 360k, face bits vs
6 pins/um, hops at <=450 um, new die bit-mm vs today (same metric). (iv) option B (2:1 on <=50%-duty links) add-on.
Usage: hub_locality.py die_plan.json duty.json out.json"""
import json,sys,math,re,collections
P=json.load(open(sys.argv[1]));D=json.load(open(sys.argv[2]))
parts={x["name"]:x for x in P["partitions"]};PT=P["partition_types"]
def centre(n):
  x=parts[n];w,h=PT[x["type"]]["outline_um"];return (x["origin_um"][0]+w/2,x["origin_um"][1]+h/2)
def outline(n): return PT[parts[n]["type"]]["outline_um"]
ports={q["id"]:q for q in P["ports"]}
GROUPS=[("vm_bank",r"vmb|vmdel|vmm|vmfc"),("vms",r"hb_vms"),("calendar",r"calendar"),("svg_vmks",r"svg|vmks"),("pc_ctl",r"ctl_Q_p"),
 ("su",r"pgp|sucore|subr|cxrc|cxij|sfus"),("cij",r"cij"),("coll",r"hb_coll|hcoll"),("idx",r"hb_idx|mu_keybuf"),("sfu_store",r"sfup"),("hc",r"u_hc_|hleaf"),
 ("sm_xload",r"xl_Q|xq_Q|smw"),("wb",r"wbk"),("dma",r"dbk"),("quant",r"quant"),("mu",r"mu_fused")]
def group(n):
  for g,r in GROUPS:
    if re.search(r,n): return g
  return "other"
UNITS=[("coll","COLL"),("cij","COLL"),("su","SU"),("sfu_store","SU"),("svg_vmks","SM"),("sm_xload","SM"),("wb","SM"),("dma","DMA"),("idx","IDX"),
 ("mu","FUSED"),("quant","FUSED"),("hc","HC")]
def duty_of(g):
  u=dict(UNITS).get(g);return (D["unit_duty"][u] if u else D["unit_duty_vm_aggregate"]),(u or "VM")
REACH=450.0;CELL_UM2=0.30;UTIL=0.6;HARD_FILL=0.70;SPAN_MAX=3000.0
out={"scope":"ESTIMATE only (no build, no RTL, no adoption); positions = anchor partition centres (slice abutting its client); UNCHECKED model",
     "plan":sys.argv[1],"types":{}}
for hub,tn in (("NW_hub","q_hub_nw"),("NE_hub","q_hub_ne")):
  t=PT[tn];hx,hy=parts[hub]["origin_um"];W,H=t["outline_um"];mir=parts[hub]["orient"]=="MY"
  def die_xy(pt): return ((hx+W-pt[0]) if mir else hx+pt[0], hy+pt[1])
  # face bus -> lane end partition
  bus2end={}
  for l in P["lanes"]:
    ps=[ports[i] for i in l["ports"]]
    for k,q in enumerate(ps):
      if q["src"]["part"]==hub: bus2end[q["src"]["bus"]]=(ps[-1]["dst"]["part"],sum(math.dist(centre(a["src"]["part"]) if a["src"]["part"] in parts else (0,0),centre(a["dst"]["part"]) if a["dst"]["part"] in parts else (0,0)) for a in ps[k:]))
      if q["dst"]["part"]==hub: bus2end[q["dst"]["bus"]]=(ps[0]["src"]["part"],0)
  hard={h["inst"] for h in t["hard_cores"]};harea=collections.Counter()
  def logical(n): return re.sub(r"__q\d$","",n.split(".")[0])
  for h in t["hard_cores"]: harea[logical(h["inst"])]+=h["outline_um"][0]*h["outline_um"][1]
  soft={c["inst"]:c["cells"] for c in t["contents"] if not any(h==c["inst"] or h.startswith(c["inst"]+"_") or h.startswith(c["inst"]+".") for h in hard)}
  M=collections.Counter();ext=collections.defaultdict(collections.Counter);old_bitum=0.0;unres=collections.Counter()
  links=[]
  for s in t["internal_stations"]:
    ends=[]
    for nm in (s["launch"],s["capture"]):
      if nm.startswith("face bus"):
        b=nm.split()[-1];e=bus2end.get(b)
        if e is None: unres[b]+=s["bits"];ends.append(("X","?"));continue
        ends.append(("X",e[0]))
      else: ends.append(("C",logical(nm)))
    pts=[s["from_um"]]+s["regs_um"]+[s["to_um"]]
    L=sum(abs(a[0]-c[0])+abs(a[1]-c[1]) for a,c in zip(pts,pts[1:]));old_bitum+=s["bits"]*L
    links.append((ends[0],ends[1],s["bits"],s.get("serial_k") or 1))
    if ends[0][0]=="C" and ends[1][0]=="C": M[(ends[0][1],ends[1][1])]+=s["bits"]
    for a,b in (ends,ends[::-1]):
      if a[0]=="C" and b[0]=="X": ext[a[1]][b[1]]+=s["bits"]
  # external lane length outside the hub (today), per bus: counted once per bit of the lane width
  old_ext_bitum=0.0
  for b,(e,L) in bus2end.items():
    w=next((x["width"] for x in t["buses"] if x["name"]==b),0);old_ext_bitum+=w*L
  cores=sorted(set([n for k in M for n in k]+list(ext)))
  # anchors
  anchor={c:ext[c].most_common(1)[0][0] for c in cores if ext[c]}
  adj=collections.defaultdict(collections.Counter)
  for (a,b),v in M.items(): adj[a][b]+=v;adj[b][a]+=v
  for _ in range(10):
    for c in cores:
      if c in anchor: continue
      for nb,_v in adj[c].most_common():
        if nb in anchor: anchor[c]=anchor[nb];break
  for c in cores: anchor.setdefault(c,"root")
  import os
  if os.environ.get("HYBRID"):
    intb=collections.Counter()
    for (x,y),v in M.items(): intb[x]+=v;intb[y]+=v
    for c in cores:
      if sum(ext[c].values())<=intb[c] or c not in ext or not ext[c]: anchor[c]=hub
  # (i) locality shares (all station bits, internal + external)
  share=collections.Counter()
  for a,b,bits,k in links:
    A_=anchor[a[1]] if a[0]=="C" else a[1];B_=anchor[b[1]] if b[0]=="C" else b[1]
    ga=group(a[1]) if a[0]=="C" else None;gb=group(b[1]) if b[0]=="C" else None
    if A_==B_: share["local_one_client"]+=bits
    elif ga is not None and ga==gb: share["local_one_function_group"]+=bits
    else: share["die_wide"]+=bits
  totb=sum(share.values())
  cls=lambda x:re.sub(r"\d+$","",x.split("_",1)[-1]) if x in parts else x
  sh_by_class=collections.Counter()
  for a,b,bits,k in links:
    A_=anchor[a[1]] if a[0]=="C" else a[1];B_=anchor[b[1]] if b[0]=="C" else b[1]
    if A_==B_: sh_by_class[cls(A_)]+=bits
  # (ii) slices: key = anchor; split by group if span > SPAN_MAX
  def area(cs): return sum(harea[c] for c in cs)/HARD_FILL+sum(soft.get(c,0) for c in cs)*CELL_UM2/UTIL
  sl=collections.defaultdict(list)
  for c in cores: sl[anchor[c]].append(c)
  slices={}
  for an,cs in sl.items():
    if math.sqrt(area(cs))<=SPAN_MAX: slices[an]=cs;continue
    byg=collections.defaultdict(list)
    for c in cs: byg[group(c)].append(c)
    for g,cg in byg.items(): slices[f"{an}/{g}"]=cg
  of={c:s for s,cs in slices.items() for c in cs}
  def spos(s):
    an=s.split("/")[0];return centre(an) if an in parts else (hx+W/2,hy+H/2)
  # (iii) per slice numbers, with and without B
  XING=[]
  def evaluate(Bmode):
    rows={};bitum=0.0;hops_max=0;hops=collections.Counter()
    face=collections.Counter();anc_face=collections.Counter();regs=collections.Counter()
    for a,b,bits,k in links:
      d,u=0,None
      ga=group(a[1]) if a[0]=="C" else None;gb=group(b[1]) if b[0]=="C" else None
      dd=[duty_of(g)[0] for g in (ga,gb) if g];du=max(dd) if dd else 1.0
      bb=bits/2 if (Bmode and du*k<=0.5) else bits
      sa=of[a[1]] if a[0]=="C" else None;sb=of[b[1]] if b[0]=="C" else None
      pa=spos(sa) if sa else (centre(a[1]) if a[1] in parts else (hx+W/2,hy+H/2))
      pb=spos(sb) if sb else (centre(b[1]) if b[1] in parts else (hx+W/2,hy+H/2))
      dist=abs(pa[0]-pb[0])+abs(pa[1]-pb[1])
      if sa and sb and sa==sb: dist=0.0
      if (sa and not sb and sa.split("/")[0]==b[1]) or (sb and not sa and sb.split("/")[0]==a[1]): dist=0.0  # slice abuts its own client
      span=lambda s:math.sqrt(area(slices[s]))
      eff=dist+((span(sa) if sa else 0)+(span(sb) if sb else 0))/2   # in-slice reach to the face
      XING.append(dict(a=sa or a[1],b=sb or b[1],pa=pa,pb=pb,bits=bb,dist_um=dist,eff_um=eff)) if not Bmode and (sa!=sb) else None
      bitum+=bb*eff;h=math.ceil(eff/REACH);hops[h]+=bb;hops_max=max(hops_max,h)
      for s,o in ((sa,sb),(sb,sa)):
        if s and s!=o:
          face[s]+=bb
          if o is None and (a[1] if s==sb else b[1])==s.split("/")[0]: anc_face[s]+=bb
          regs[s]+=1.3*bb*max(0,math.ceil(span(s)/2/REACH))
    for s,cs in slices.items():
      sp=max(50.0,math.sqrt(area(cs)));cells=sum(soft.get(c,0) for c in cs)+regs[s]
      rows[s]=dict(cores=len(cs),span_um=round(sp),hard_mm2=round(sum(harea[c] for c in cs)/1e6,2),soft_cells=round(cells),
                   face_bits=round(face[s]),face_ratio_perimeter=round(face[s]/(6*4*sp),2),anchor_face_bits=round(anc_face[s]),
                   anchor_face_ratio_one_side=round(anc_face[s]/(6*sp),2),over_360k=cells>360000)
    return dict(slices=rows,new_bitmm=round(bitum/1e3),hops_bits=dict(sorted(hops.items())),hops_max=hops_max,
                worst_perimeter_ratio=max(r["face_ratio_perimeter"] for r in rows.values()),
                worst_anchor_side_ratio=max(r["anchor_face_ratio_one_side"] for r in rows.values()),
                slices_over_360k=sum(r["over_360k"] for r in rows.values()),n_slices=len(rows))
  # straddle flags: logical cores whose clients split across slices (no single anchor > 60 % of its external bits)
  straddle={c:dict(ext[c].most_common(4)) for c in cores if ext[c] and ext[c].most_common(1)[0][1]<0.6*sum(ext[c].values())}
  res=dict(station_bits=totb,locality_share={k:round(v/totb,3) for k,v in share.items()},local_bits_by_client_class=dict(sh_by_class.most_common()),
           unresolved_face_bus_bits=sum(unres.values()),
           today_bitmm_hub_internal=round(old_bitum/1e3),today_bitmm_hub_external_lanes=round(old_ext_bitum/1e3),
           anchors={c:anchor[c] for c in cores},core_external=dict((c,dict(ext[c].most_common(3))) for c in cores),
           straddle_cores=straddle,
           matrix_top=[(a,b,v) for (a,b),v in M.most_common(40)],
           group_matrix=sorted([(ga,gb,v) for (ga,gb),v in collections.Counter({(group(a),group(b)):0 for (a,b) in M}).items()]),
           plan=evaluate(False),plan_B=evaluate(True))
  res['crossings']=XING;res['root_xy']=centre('root')
  gm=collections.Counter()
  for (a,b),v in M.items(): gm[(group(a),group(b))]+=v
  res["group_matrix"]=[(a,b,v) for (a,b),v in gm.most_common(30)]
  out["types"][tn]=res
  print(tn,json.dumps({k:res[k] for k in ("station_bits","locality_share","local_bits_by_client_class","unresolved_face_bus_bits","today_bitmm_hub_internal","today_bitmm_hub_external_lanes")}))
  for m in ("plan","plan_B"):
    r=res[m];print(" ",m,{k:v for k,v in r.items() if k!="slices"})
  for s,r in sorted(res["plan"]["slices"].items(),key=lambda z:-z[1]["face_bits"]): print("   ",s,r)
  print("  straddle",res["straddle_cores"])
json.dump(out,open(sys.argv[3],"w"),indent=1)
