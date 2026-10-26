import sys, json, os, re
wt, die = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(wt, "tools/autopilot"))
import ownership as O
plan = json.load(open(os.path.join(wt, "physical/die_plan", die, "die_plan.json")))
T = plan["partition_types"]
n = {}
for p in plan["partitions"]: n[p["type"]] = n.get(p["type"], 0) + 1
def fam(k): return re.sub(r"(_v\d+|_r\d+)+$", "", k)
fams = {}
for k in T: fams.setdefault(fam(k), []).append(k)
def comp(t):
    return dict(outline=t.get("outline_um"), cores=sorted((c["inst"], c["module"]) for c in t.get("hard_cores", [])),
      contents=sorted(O._canon(O._strip(c, O.CONTENT_GEOM)) for c in t.get("contents", [])),
      buses=sorted(O._canon(O._strip(b, O.BUS_GEOM)) for b in t.get("buses", [])),
      slots=sorted(O._canon(O._strip(s, O.SLOT_GEOM)) for s in t.get("ft_slots", [])),
      sources=sorted(t.get("sources", [])), reset=t.get("reset", {}).get("sync_stages"),
      busgeom=sorted(O._canon(O._strip(b, {"note"})) for b in t.get("buses", [])),
      slotgeom=sorted(O._canon(O._strip(x, O.SLOT_INTERNAL)) for x in t.get("ft_slots", [])))
for f, ks in sorted(fams.items()):
    ks = sorted(ks, key=lambda x: -n.get(x, 0)); ref = ks[0]; R = comp(T[ref])
    print(f"== {f}: " + " ".join(f"{k}({n.get(k,0)})" for k in ks), "module=", T[ref].get("module"))
    for k in ks[1:]:
        C = comp(T[k]); d = []
        for key in R:
            if R[key] != C[key]:
                if isinstance(R[key], list) and key not in ("outline",):
                    a, b = set(map(str, R[key])), set(map(str, C[key]))
                    d.append(f"{key}(-{len(a-b)}+{len(b-a)})")
                else: d.append(f"{key}({R[key]} vs {C[key]})")
        print(f"   {k} vs {ref}: {' '.join(d) or 'IDENTICAL'}")
