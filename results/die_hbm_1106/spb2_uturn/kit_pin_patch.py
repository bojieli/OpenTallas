#!/usr/bin/env python3
"""Kit-local application of a pin-window plan event to an already generated partition kit (DIE-HBM-82-SPB, d44v part 54).
kit_pin_patch.py OLD_PLAN.json NEW_PLAN.json KIT TYPE BUS[,BUS]   (run from the repo root)
Rewrites only the rows of BUS in pins.json, io.tcl, plan_pins.json, audit_pins.json and refreshes freeze.json, with the
same gen_phys functions the generator uses.  Refuses unless the OLD plan regenerates the kit's current rows exactly."""
import hashlib, json, re, sys
from pathlib import Path
sys.path[:0] = ["tools/die_plan"]
import schema as S, gen_phys as G, kit_contract as KC
po, pn, kd, tn, buses = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4], set(sys.argv[5].split(","))
Po, Pn = S.Plan(S.load(po), po), S.Plan(S.load(pn), pn)
old = [p for p in G.type_pins(Po, tn) if p[0] in buses]; new = [p for p in G.type_pins(Pn, tn) if p[0] in buses]
assert old and len(old) == len(new), (len(old), len(new))
key = lambda p: (p[0], p[1])
# pins.json
pj = json.loads((kd / "pins.json").read_text())
cur = sorted((r["bus"], r["bit"], r["layer"], r["x"], r["y"], r["face"]) for r in pj if r["bus"] in buses)
assert cur == sorted(old, key=key) or cur == sorted(old), "pins.json rows != old plan type_pins"
nm = {key(p): p for p in new}
for r in pj:
    if r["bus"] in buses:
        b, i, l, x, y, f = nm[(r["bus"], r["bit"])]; r.update(layer=l, x=x, y=y, face=f)
(kd / "pins.json").write_text(json.dumps(pj) + "\n")
# io.tcl
pat = lambda n: re.compile(r"^place_pin -pin_name \{(%s)\[(\d+)\]\} " % "|".join(map(re.escape, n)))
gen_lines = lambda P, pins: {m.group(1, 2): l for l in G.io_tcl(P, tn, pins).splitlines() if (m := pat(buses).match(l))}
go, gn = gen_lines(Po, old), gen_lines(Pn, new)
io = (kd / "io.tcl").read_text().splitlines(); hit = 0
for j, l in enumerate(io):
    m = pat(buses).match(l)
    if m:
        assert l == go[m.group(1, 2)], ("io.tcl line != old plan", l, go[m.group(1, 2)]); io[j] = gn[m.group(1, 2)]; hit += 1
assert hit == len(old), (hit, len(old))
(kd / "io.tcl").write_text("\n".join(io) + "\n")
# plan_pins.json (pin centres)
isb = lambda n: n.split("[")[0] in buses
ro = {r["name"]: r for r in G.plan_pin_records(Po, tn, old) if isb(r["name"])}
rn = {r["name"]: r for r in G.plan_pin_records(Pn, tn, new) if isb(r["name"])}
ppd = json.loads((kd / "plan_pins.json").read_text()); hit = 0
for j, r in enumerate(ppd["pins"]):
    if isb(r["name"]):
        assert r == ro[r["name"]], (r, ro[r["name"]]); ppd["pins"][j] = rn[r["name"]]; hit += 1
assert hit == len(old)
body = json.dumps(ppd, indent=1) + "\n"; (kd / "plan_pins.json").write_text(body)
# audit_pins.json (face rows)
au = json.loads((kd / "audit_pins.json").read_text()); hit = 0
for r in au:
    if r.get("bus") in buses:
        b, i, l, x, y, f = nm[(r["bus"], r["bit"])]; r.update(layer=l, x=x, y=y, face=f); hit += 1
assert hit == len(old), hit
(kd / "audit_pins.json").write_text(json.dumps(au, indent=1) + "\n")
# freeze.json
fz = json.loads((kd / "freeze.json").read_text()); w, h = fz["outline_um"]
fz["pins_sha256"] = hashlib.sha256(body.encode()).hexdigest(); fz["pins_canon_sha256"] = KC._canon(ppd["pins"], [w, h])
placed = KC._canon(KC.placed_pins(kd), [w, h]); expect = KC._canon(KC.slice_expected(kd, ppd["pins"]), [w, h])
assert placed == expect, "io.tcl placed pins != plan pins after patch"
(kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
print(f"{tn}: {len(old)} pins of {sorted(buses)} moved; io.tcl/plan_pins/audit_pins/pins.json patched; freeze canon {fz['pins_canon_sha256'][:12]}; kit_contract placed==expected")
