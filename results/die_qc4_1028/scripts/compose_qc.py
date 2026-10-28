# DIE-QC-4: grp-map plan delta = QC-SLICECLK compose.py recipe (main clock_landing_plan.compose) on the 2,558-crossing table
import json, sys, time
from pathlib import Path
MT, PLAN, TAB, OUT = sys.argv[1:5]
sys.path.insert(0, MT + "/tools/die_plan")
import clock_landing_plan as CP
t = time.time(); pp = Path(PLAN)
P = json.load(open(pp)); T = json.load(open(TAB))
raw, side = CP.compose(P, T, plan_path=pp.resolve())
Path(OUT).mkdir(exist_ok=True)
json.dump(raw, open(OUT + "/landed_plan.json", "w")); json.dump(side, open(OUT + "/landed_sidecar.json", "w"), indent=1)
print("compose OK", round(time.time() - t), "s", "types", len(P["partition_types"]), "->", len(raw["partition_types"]))
