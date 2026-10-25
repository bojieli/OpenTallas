"""LEAF4: hard_cores[].obs_max of the 72 leaf types from each core LEF OBS ceiling (closed views: lane_pr / vsw / rxsf / rxsb
M5, 512x128 SRAM M4; the plan-LEF leaf cores vn_a / vn_b / vq / vs / ve_m / ve_s M7)."""
import json,re,subprocess,sys
from pathlib import Path; WT=str(Path(__file__).resolve().parents[5])
P=json.load(open(sys.argv[1])); cache={}
def ceil(lef):
    if lef not in cache:
        t=subprocess.run(["git","-C",WT,"show","HEAD:"+lef],capture_output=True,text=True).stdout
        obs=re.findall(r"\n\s*OBS\b(.*?)\n\s*END\b",t,re.S)
        L=[int(x) for o in obs for x in re.findall(r"LAYER M(\d+)",o)]
        cache[lef]="M%d"%max(L) if L else "M7"
    return cache[lef]
for tn,T in P["partition_types"].items():
    if tn.startswith("ot_s81sl_leaf__t"):
        for c in T["hard_cores"]: c["obs_max"]=ceil(c["lef"])
json.dump(P,open(sys.argv[2],"w"),indent=0)
print({k.split("/")[-1]:v for k,v in cache.items()})
