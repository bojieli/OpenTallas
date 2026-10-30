# per-type resize_undersized_bands digest (main vs branch); PHY regions + band overlaps (branch only)
import sys,json,hashlib
code,plan,side=sys.argv[1],sys.argv[2],sys.argv[3]
sys.path.insert(0,code)
import schema as S
import importlib.util
cpfile=sys.argv[4] if len(sys.argv)>4 else code+"/clock_landing_plan.py"
sp=importlib.util.spec_from_file_location("CP_cmp",cpfile);CP=importlib.util.module_from_spec(sp);sp.loader.exec_module(CP)
p=json.load(open(plan));sd=json.load(open(side))
types=sorted(tn for tn,t in p["partition_types"].items() if t.get("clock",{}).get("landing_contract",{}).get("bands") and tn in sd["collector"]["types"])
if hasattr(CP,"phy_supply_rects"):
    P=S.Plan(p)
    for tn in types:
        r=CP.phy_supply_rects(P,tn)
        if r:
            bs=p["partition_types"][tn]["clock"]["landing_contract"]["bands"]
            print("PHY",tn,r,"overlap",[k for k,b in bs.items() if b.get("rect_um") and any(CP._rect_overlap(b["rect_um"],o) for o in r)])
for tn in types:
    try:
        new,rep=CP.resize_undersized_bands(p,sd,[tn]);d=hashlib.sha256(json.dumps(new["partition_types"][tn],sort_keys=True).encode()).hexdigest()[:12]
        print("T",tn,d,len(rep))
    except ValueError as e:print("T",tn,"ERR",str(e)[:80])
