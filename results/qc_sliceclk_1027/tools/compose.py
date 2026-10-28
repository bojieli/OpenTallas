import json,sys,time
W="/srv/opentallas-scratch2/claude/wt/qc-sliceclk-1027"
sys.path.insert(0,W+"/tools/die_plan")
import clock_landing_plan as CP
from pathlib import Path
t=time.time(); pp=Path(W+"/physical/die_plan/qwen_compute/die_plan.json")
P=json.load(open(pp)); T=json.load(open("fs/landed_crossings.json"))
raw,side=CP.compose(P,T,plan_path=pp.resolve())
json.dump(raw,open("pd/landed_plan.json","w")); json.dump(side,open("pd/landed_sidecar.json","w"),indent=1)
print("compose OK",round(time.time()-t),"s")
