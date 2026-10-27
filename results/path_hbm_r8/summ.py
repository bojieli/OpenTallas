import json,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/path-hbm-r8-1026/tools/die_plan')
import plan_cut as PC
if sys.argv[1]=="base":
    P=json.load(open(sys.argv[2]))["partition_types"]
    for tn in sys.argv[3].split(","):
        t=P[tn]; W,H=t["outline_um"]
        for b in (True,False):
            c=PC._cut_profile(W,H,PC._nets(t),PC._cores(t),blocked=b,per_sink=True)
            print("b1e2",tn,"per-sink","blocked" if b else "unblocked","x",c["x"]["max_use"],c["x"]["bits"],"face",c["x"]["face_bits"],"y",c["y"]["max_use"])
else:
  for d in sys.argv[2:]:
    r=json.load(open(d+"/r8_delta_report.json"))
    for tn,t in r["plan_cut"]["types"].items():
        a=t["cut_per_sink"];b=t["cut_per_sink_unblocked"]
        print(d.split("/")[-1],tn,"per-sink blocked x",a["x"]["max_use"],"y",a["y"]["max_use"],"| unblocked x",b["x"]["max_use"],"bits",b["x"]["bits"],"face",b["x"]["face_bits"],"y",b["y"]["max_use"],"| area",r["hubs"].get(tn,{}).get("core_area_frac"))
