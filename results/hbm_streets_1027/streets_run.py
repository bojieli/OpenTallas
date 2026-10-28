"""HBM-STREETS-1 driver: G0C street rule only (check.check_streets) on a plan, json summary out."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import check, schema as S
plan = Path(sys.argv[2]); out = Path(sys.argv[3]); builds = sys.argv[4:]
t = time.time()
raw = S.load(str(plan))
P = S.Plan(raw, plan)
geo = {lid: check.lane_geometry(P, lid) for lid in P.lanes}
R = check.Report(True)
s = check.check_streets(P, R, plan.parent, builds, geo, png=out.with_suffix(".png"))
s["errors"] = [i["msg"] for i in R.errors()]
s["warns"] = [i["msg"] for i in R.items if i["level"] != "ERROR"]
s["plan"] = str(plan); s["sec"] = round(time.time() - t, 1)
out.write_text(json.dumps(s, indent=1, default=str))
print(plan, "errors", len(R.errors()), s["counts"], "cores", s["cores"], "over", s["cores_over_reach"], "streets", s["streets"], "sec", s["sec"])
