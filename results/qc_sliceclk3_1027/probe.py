import sys,json,time
sys.path.insert(0,"tools/die_plan")
import schema as S, die_trial as DT
from pathlib import Path
pp="physical/die_plan/qwen_compute/die_plan_sliceclk.json"
P=S.Plan(S.load(pp),Path(pp))
R=json.load(open("/srv/opentallas-scratch2/claude/qc-sliceclk-1027/fs/regions.json"))["part_region"]
t=time.time()
nodes,segs,legs,m=DT.clock_kit(P,sys.argv[1],600.0,405.0,True,True,False,R,True,50.0)
print("sec",round(time.time()-t))
print(json.dumps(m,indent=None)[:6000])
