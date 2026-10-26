"""what-if (diagnostic, not a delta): on an R10 output plan, serialise core-core hub stations longer than --min-um by k."""
import json,sys,math,copy
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/path-hbm-r10-1026/tools/die_plan")
import hbm_r9_delta as R9
P=json.load(open(sys.argv[1]+"/die_plan.json")); minum=float(sys.argv[2])
def face(p,W,H): return p[1]<=.5 or p[1]>=H-.5 or p[0]<=.5 or p[0]>=W-.5
for tn in ("q_hub_nw","q_hub_ne"):
  t=P["partition_types"][tn]; W,H=t["outline_um"]
  for k in (1,2,3,4):
    st=copy.deepcopy(t["internal_stations"]); n=0
    for s in st:
      if face(s["from_um"],W,H) or face(s["to_um"],W,H) or s.get("serial_k"): continue
      if abs(s["from_um"][0]-s["to_um"][0])+abs(s["from_um"][1]-s["to_um"][1])>minum and k>1:
        s["bits"]=math.ceil(s["bits"]/k); n+=1
    u=R9.cut(dict(outline_um=[W,H],hard_cores=t["hard_cores"],internal_stations=st))["blocked"]
    print(tn,"k_cc",k,"serialised",n,"x",u["x"]["max_use"],"y",u["y"]["max_use"])
