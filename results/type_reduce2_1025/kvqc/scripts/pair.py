import sys, json, os
sys.path.insert(0, os.path.join(sys.argv[1], "tools/autopilot")); import ownership as O
plan = json.load(open(os.path.join(sys.argv[1], "physical/die_plan", sys.argv[2], "die_plan.json"))); T = plan["partition_types"]
def comp(t):
    return dict(outline=t.get("outline_um"), cores=sorted((c["inst"], c["module"]) for c in t.get("hard_cores", [])),
      contents=sorted(O._canon(O._strip(c, O.CONTENT_GEOM)) for c in t.get("contents", [])),
      buses=sorted(O._canon(O._strip(b, O.BUS_GEOM)) for b in t.get("buses", [])),
      slots=sorted(O._canon(O._strip(s, O.SLOT_GEOM)) for s in t.get("ft_slots", [])),
      sources=sorted(t.get("sources", [])), busgeom=sorted(O._canon(O._strip(b, {"note"})) for b in t.get("buses", [])),
      slotgeom=sorted(O._canon(O._strip(x, O.SLOT_INTERNAL)) for x in t.get("ft_slots", [])))
for pr in sys.argv[3:]:
    a, b = pr.split(":"); R, C = comp(T[a]), comp(T[b]); d = []
    for key in R:
        if R[key] != C[key]:
            if key == "outline": d.append(f"outline({R[key]} vs {C[key]})")
            else:
                x, y = set(map(str, R[key])), set(map(str, C[key])); d.append(f"{key}(-{len(x-y)}+{len(y-x)})")
    print(f"{a} vs {b}: {' '.join(d) or 'IDENTICAL'}")
