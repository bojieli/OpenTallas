import sys, json, copy, collections
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import check as C, schema as S
from pathlib import Path
pd = Path(sys.argv[2]); raw = json.loads((pd/"die_plan.json").read_text())
P = S.Plan(copy.deepcopy(raw), pd/"die_plan.json")
col = []
C.check_core_faces(P, C.Report(True), str(pd), None, collect=col)
hcs = {(tn, hc["inst"]): hc for tn, t in raw["partition_types"].items() for hc in t.get("hard_cores", [])}
bad = {(r["type"], r["inst"], r["port"]) for r in col if r["mean"] < C.FACE_AWAY_COS}
keys = {(hcs[(t,i)]["pins_file"], hcs[(t,i)].get("orient","R0"), p) for t,i,p in bad}
for r in col:
    hc = hcs[(r["type"], r["inst"])]
    k = (hc["pins_file"], hc.get("orient","R0"), r["port"])
    if k in keys:
        ws = sorted(r["dirs"], key=lambda d: -1)[:2]
        print(k[0][6:45], k[1], k[2], r["type"], r["inst"], "o=", [round(v) for v in hc["origin_um"]], "faces", sorted(set(r["faces"])), "mean %.2f" % r["mean"], "best", C.best_face(r["dirs"]), [(w[0][:24], round(w[1],2), round(w[2],2)) for w in r["dirs"][:2]])
