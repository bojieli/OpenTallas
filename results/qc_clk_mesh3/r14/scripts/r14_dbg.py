import sys, json
sys.path.insert(0, "/w/die_plan")
import schema as S, die_clock_mesh as DCM, die_clock_128 as C128
from pathlib import Path
P = S.Plan(S.load("inputs/candidate_oneqc0733.json"), Path("inputs/candidate_oneqc0733.json"))
spec = json.load(open(sys.argv[1]))
orig = C128.TrackRouter.place
def place(self, layer, ideal, a0, a1, net):
    r = orig(self, layer, ideal, a0, a1, net)
    if any(k in net for k in sys.argv[2:]): print("PLACE", net, layer, round(ideal,3), round(min(a0,a1),3), round(max(a0,a1),3), "->", r[0], r[1])
    return r
C128.TrackRouter.place = place
try:
    DCM.build_explicit(spec, P=P, ndr="16w")
    print("BUILT")
except C128.PlanError as e:
    print("ERR", e)
