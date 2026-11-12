"""plan-level tap/sink histogram: per type, taps.density_taps planned sinks (kit split rule) -> TSV"""
import json, sys, os
repo, plan, out = sys.argv[1], sys.argv[2], sys.argv[3]
types = sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] else None
os.chdir(repo)
sys.path.insert(0, os.path.join(repo, "tools/die_plan"))
import schema, taps
raw = json.load(open(plan))
P = schema.Plan(raw)
rows = []
for tn in sorted(raw["partition_types"]):
    if types and tn not in types:
        continue
    ck = raw["partition_types"][tn].get("clock", {})
    mode = ck.get("tap_mode")
    try:
        if mode == "density":
            res = taps.density_taps(P, tn)
            for port, x, y, n, r in res:
                rows.append((tn, mode, port, x, y, n, r))
        else:
            g = schema.tap_grid(P, tn)
            rows.append((tn, mode, "n_taps=%d" % len(g), "", "", -1, ""))
    except Exception as e:
        rows.append((tn, mode, "ERR " + repr(e)[:200], "", "", -1, ""))
    print(tn, flush=True, file=sys.stderr)
with open(out, "w") as f:
    for r in rows:
        f.write("\t".join(str(v) for v in r) + "\n")
