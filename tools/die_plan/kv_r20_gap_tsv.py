"""CLOCK-KV-R20: the clock_entry FAIL cores (no plan tap + no native clock-pin metadata) ranked by the seam tap
pairs their gate tap carries (die_sta_related seam class, unique (launch, capture) tap pairs touching the tap that
map_cores_to_taps assigns the core instance to), summed over every die instance of the partition type."""
import sys, json, pickle
from collections import defaultdict
import die_sta_related as R
rows_f, pkl, plan_path, out = sys.argv[1:5]
ALLROWS = json.load(open(rows_f))
d = pickle.load(open(pkl, "rb")); tt, ff = dict(zip(d["classes"], d["recs"]))["seam"]
pairs = set((k[0], k[1]) for k in ff)
seam_bits = defaultdict(int)
pair_by_tap = defaultdict(int)
for a, b in pairs:
    pair_by_tap[a] += 1; pair_by_tap[b] += 1
plan = json.load(open(plan_path))
import schema as S
P = S.Plan(plan)
M = json.load(open(sys.argv[5]))
taps = {t["port"]: dict(part=t["part"], xy_um=t["xy"]) for t in M["taps"]}
cmap = R.map_cores_to_taps(plan, taps)
# master_plan calls core_clock_entry_check in P.types x hard_cores order: recover the type of each captured row
order = [(tn, h["inst"], h["module"]) for tn, t in P.types.items() for h in t.get("hard_cores", [])]
assert len(order) == len(ALLROWS), (len(order), len(ALLROWS))
rows = []
for (tn, inst, mod), r in zip(order, ALLROWS):
    assert (inst, mod) == (r["hard_inst"], r["hard_module"]), (inst, mod, r["hard_inst"])
    if r["verdict"] != "PASS":
        rows.append(dict(r, type=tn))
agg = defaultdict(lambda: dict(instances=0, seam_pairs=0, parts=[]))
for (n, inst), (mod, port, dist, pins) in cmap.items():
    t = P.parts[n]["type"]
    g = agg[(t, inst)]; g["instances"] += 1; g["seam_pairs"] += pair_by_tap.get(port, 0); g["parts"].append(n)
seen = set(); out_rows = []
for r in rows:
    key = (r["type"], r["hard_inst"])
    if key in seen:
        continue
    seen.add(key)
    g = agg.get(key, dict(instances=0, seam_pairs=0, parts=[]))
    out_rows.append((g["seam_pairs"], r["type"], r["hard_inst"], r["hard_module"], g["instances"],
                     r.get("issue") or "; ".join(r.get("issues", [])), r.get("pins_file", ""),
                     ",".join(map(str, r.get("entry_xy") or [])), ",".join(sorted(g["parts"])[:4]) + ("..." if len(g["parts"]) > 4 else "")))
out_rows.sort(key=lambda x: (-x[0], x[1], x[2]))
with open(out, "w") as f:
    f.write("rank\tseam_pairs\tpart_type\tcore_inst\tcore_module\tdie_instances\tissue\tpins_file\tentry_um\tparts\n")
    for i, x in enumerate(out_rows, 1):
        f.write(f"{i}\t" + "\t".join(map(str, x)) + "\n")
mods = defaultdict(lambda: [0, 0, 0])
for x in out_rows:
    m = mods[x[3]]; m[0] += 1; m[1] += x[4]; m[2] += x[0]
print("fail rows", len(rows), "unique (type,inst)", len(out_rows), "die instances", sum(x[4] for x in out_rows))
for m, v in sorted(mods.items(), key=lambda kv: -kv[1][2])[:15]:
    print(m, "rows", v[0], "inst", v[1], "seam_pairs", v[2])
