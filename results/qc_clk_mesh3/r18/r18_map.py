import json, sys
A, B = sys.argv[1:3]
T = json.load(open(f"{A}/fold/taps.json")); P = json.load(open(f"{B}/place.json"))
E = json.load(open(f"{A}/fold/edges.json"))["edges"]
dm = [abs(P[f"ckt_{v['cell']}_0"]["x"] - v["site"][0]) + abs(P[f"ckt_{v['cell']}_0"]["y"] - v["site"][1]) for v in T.values()]
print("tap site vs place.json manh max", round(max(dm), 3), "n", len(dm), "kinds", {P[f"ckt_{v['cell']}_0"]["plan_kind"] for v in T.values()})
miss = sum(1 for v in E.values() if v["ns"] == "t" for ci in v["cells"] if f"ckt_{ci}_0" not in P)
print("t edges", sum(v["ns"] == "t" for v in E.values()), "missing cells", miss)
