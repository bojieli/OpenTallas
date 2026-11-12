"""m89 landing table follow-up (X-TIER-OTC form (d)): the clock-landing table (asbuilt clock_landing_table / gen
--clock-landing) names the landed input bus of each collector type.  m89_form splits ft slot <s> into bays <s>b<j>
and the landing ring moves to bay 0 (<s>b0_i), so every whole-word <s>_i token of that type's collector entry
(local_sources name/ready/fault, bands, bus_geometry, mask) becomes <s>b0_i.  Nothing else changes.
  python3 m89_landing.py FORM_D_PLAN TABLE_IN TABLE_OUT"""
import json, re, sys
plan, tin, tout = sys.argv[1:4]
P = json.load(open(plan)); D = json.load(open(tin))
types = (D.get("collector") or {}).get("types", {})
rep = {}
for tn, ent in types.items():
    pt = P["partition_types"].get(tn)
    if not pt:
        continue
    names = {s["name"] for s in pt.get("ft_slots", [])}
    split = sorted({m.group(1) for n in names for m in [re.fullmatch(r"(ft\d+)b0", n)] if m and m.group(1) not in names})
    if not split:
        continue
    s = json.dumps(ent); n0 = 0
    for b in split:
        s, k = re.subn(rf"(?<![A-Za-z0-9]){b}_i(?![A-Za-z0-9_])", f"{b}b0_i", s); n0 += k
        s, k = re.subn(rf"_{b}_i(?![A-Za-z0-9_])", f"_{b}b0_i", s); n0 += k
    if n0:
        e = json.loads(s)
        # the moved sources take the plan's (m89_form) site: xy / pin / band of the bay-0 ring
        lc = {x["name"]: x for x in ((pt.get("clock") or {}).get("landing_contract") or {}).get("collector_local_sources", [])}
        moved = 0
        for src in e.get("local_sources", []):
            p = lc.get(src.get("name"))
            if p and src["name"].split("b0_i")[0] in split:
                for k in ("xy_um", "pin_xy_um", "band", "tap", "status_pins_xy_um"):
                    if k in p: src[k] = p[k]
                    elif k in src and k == "status_pins_xy_um": src.pop(k)
                moved += 1
        types[tn] = e; rep[tn] = dict(slots=split, tokens=n0, sources_resited=moved)
json.dump(D, open(tout, "w"))
print("M89_LANDING", json.dumps(rep))
