"""Same native pins/faces/order, width sized for existing six-pin/um rule; not route-qualified."""
import json,pathlib,collections,math
B=pathlib.Path(__file__).parent;P=json.load(open(B/"c15_ref/die_plan.json"));oldW,H=181.44,276.48;W=362.88
fname="ot_hgi_sm_xload_xq_pegress__181.44x276.48__content_trial.json"
a=json.load(open(B/"c15_ref/cores"/fname));before={q["name"]:dict(q) for q in a}
def face(q):
 d=[q["x"],oldW-q["x"],q["y"],H-q["y"]];return "WESN"[d.index(min(d))]
g=collections.defaultdict(list)
for q in a:g[face(q)].append(q)
def tracks(lo,hi,n,exclude=None):
 xs=[round(.024+k*.048,3) for k in range(math.ceil((lo-.024)/.048),math.floor((hi-.024)/.048)+1)]
 xs=[x for x in xs if exclude is None or not exclude[0]<=x<=exclude[1]]
 assert len(xs)>=n
 return [xs[min(len(xs)-1,int(i*len(xs)/n))] for i in range(n)]
clks=[q for q in g["N"] if q["name"].startswith("clk")];data=[q for q in sorted(g["N"],key=lambda q:q["x"]) if q not in clks]
for q,x in zip(data,tracks(8.64,W-8.64,len(data))):q["x"]=x
# Preserve the unresolved five real clock pins and their order. Their source contract remains a build blocker.
for i,q in enumerate(sorted(clks,key=lambda q:q["x"])):q.update(x=round(W/2-.168+.096*i,3),y=138.264)
for q in g["E"]:q["x"]=round(W-.019,3)
for q,x in zip(sorted(g["S"],key=lambda q:q["x"]),tracks(8.64,W-8.64,len(g["S"]))):q["x"]=x
newname="ot_hgi_sm_xload_xq_pegress__362.88x276.48__pin6_trial.json"
O=B/"xq_pin6_center_trial";O.mkdir(exist_ok=True);(O/"cores").mkdir(exist_ok=True)
for f in (B/"c15_ref").iterdir():
 if f.is_file() and f.name!="die_plan.json" and not(O/f.name).exists():(O/f.name).symlink_to(f)
for f in (B/"c15_ref/cores").iterdir():
 if not(O/"cores"/f.name).exists():(O/"cores"/f.name).symlink_to(f)
(O/"cores"/newname).write_text(json.dumps(a,indent=1)+"\n")
instances=[];collisions=[]
for tn,t in P["partition_types"].items():
 for c in t.get("hard_cores",[]):
  if c["module"]!="ot_hgi_sm_xload_xq_pegress":continue
  old=c["origin_um"][:];c["origin_um"][0]=round(math.floor((old[0]-(W-oldW)/2)/8.64+1e-7)*8.64,3);c["outline_um"]=[W,H];c["pins_file"]="cores/"+newname
  x,y=c["origin_um"];hits=[]
  for d in t["hard_cores"]:
   if d is c:continue
   dx,dy=d["origin_um"];dw,dh=d["outline_um"]
   if x<dx+dw and x+W>dx and y<dy+dh and y+H>dy:hits.append(d["inst"])
  instances.append({"type":tn,"inst":c["inst"],"old_origin":old,"origin":c["origin_um"],"colliders":hits})
  if hits:collisions.append(instances[-1])
entries=json.load(open(B/"c15_ref/clock_entries.json"))
for tn,t in P["partition_types"].items():
 for c in t.get("hard_cores",[]):
  if c["module"]!="ot_hgi_sm_xload_xq_pegress":continue
  ports=sorted(q["name"] for q in clks)
  for tap in t["clock"]["taps"]:
   if tap["name"]!=c["inst"]:continue
   tap["merged_clock_ports"]=ports
   ex,ey=181.464,138.264
   if c.get("orient")=="MX":ey=H-ey
   tap["xy"]=[round(c["origin_um"][0]+ex,3),round(c["origin_um"][1]+ey,3)]
  e=entries[tn][c["inst"]];e.update(xy_um=[181.464,138.264],island_um=[177.12,133.92,185.76,142.56],merged_clock_ports=ports,source="Exact native pair parent ties clk/clk_c/clk_e/clk_s/clk_w to clk_eg at833ps; 5scalar ports preserved")
if (O/"clock_entries.json").is_symlink():(O/"clock_entries.json").unlink()
(O/"clock_entries.json").write_text(json.dumps(entries,indent=2)+"\n")
(O/"die_plan.json").write_text(json.dumps(P,indent=2)+"\n")
report={"basis":"C15 xq truepartner face assignments retained, all data pins same names/directions/layers/face and order; 5 native scalar clock pins at declared central island; no native port split or alias","old_outline_um":[oldW,H],"outline_um":[W,H],"clock_contract":"SOURCE COMMON PHASE CONFIRMED: native pair parent ties five scalar ports toclk_eg; actual kit/LEF still required","low_fill_reason":"pin-limited bq_d2048 must fit north face at6pins/um; actual contentstdarea6033um2","instances":instances,"body_collisions":collisions,"pins":len(a),"renamed_pins":0,"data_face_changed":0,"clock_face_changed":5,"not_qualified":"stations/clock/PG and neighbor relocation not yet regenerated"}
(O/"pin6_report.json").write_text(json.dumps(report,indent=2)+"\n");print(report)
