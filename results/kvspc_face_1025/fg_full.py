# diagnostic: full face_guard failure lists grouped by (class, bus): python3 fg_full.py KIT NETLIST OUT.json
import sys, json, re, collections, types
src = open(sys.argv[1] + "/face_guard.py").read().replace('res["fails"] = {k: v[:50] for k, v in res["fails"].items()}', 'pass')
G = types.ModuleType("fgfull"); exec(compile(src, "fgfull", "exec"), G.__dict__)
pins = json.load(open(sys.argv[1] + "/pins.json"))
res = G.guard(open(sys.argv[2]).read(), None, pins=pins)
grp = collections.defaultdict(list)
for cls, v in res["fails"].items():
    for s in v:
        b = s.split(":")[0]; m = re.match(r"(.+?)(\[(\d+)\])?$", b)
        grp[(cls, m.group(1))].append((int(m.group(3)) if m.group(3) else None, s))
out = {}
for (cls, bus), v in sorted(grp.items()):
    v.sort(key=lambda x: (x[0] is None, x[0]))
    idx = [i for i, _ in v if i is not None]
    rng = []
    for i in idx:
        if rng and rng[-1][1] == i - 1: rng[-1][1] = i
        else: rng.append([i, i])
    out[f"{cls} {bus}"] = dict(n=len(v), ranges=rng, sample=[s for _, s in v[:3]])
    print(f"{cls:13s} {bus:22s} {len(v):5d} {rng[:12]}  e.g. {v[0][1][:150]}")
json.dump(dict(counts=res["fail_counts"], groups=out, all=res["fails"]), open(sys.argv[3], "w"), indent=1)
