"""SU-CH-1 (KIT-CHAN-1 user): switch along_first core pin-face chains to leg_order channel where it is free.

usage: python3 -I to_channel.py SRC PLAN_IN PLAN_OUT TYPE_GLOB FACE:LO:HI

A chain becomes channel only when, for every bound bit, its channel Z path (istation_channel.path) has exactly the
Manhattan length of its L route.  Then the stations, the per-bit hop and the pin cycles do not change.  Only the
vertical (E/W face) or horizontal (N/S face) leg moves off the face edge into the channel band.  start_core chains,
chains on another face and chains whose leaf lies inside the band are left as they are.  The plan is then validated
(schema + KIT-CHAN-1 macro gate), and the converted and skipped chains are printed."""
import copy, fnmatch, json, sys

SRC, PIN, POUT, GLOB, CH = sys.argv[1:6]
sys.path.insert(0, SRC + "/tools/die_plan")
import gen_phys, istation_channel as IC, schema  # noqa: E402

face_want, lo, hi = CH.split(":")
lo, hi = float(lo), float(hi)
raw = json.load(open(PIN))
P = schema.Plan(copy.deepcopy(raw), path=PIN)
done, skip = {}, []
for tn, t in raw["partition_types"].items():
    if not fnmatch.fnmatch(tn, GLOB):
        continue
    pins = {}
    for name, bit, _ln, x, y, _f in gen_phys.type_pins(P, tn):
        pins.setdefault(name, {})[int(bit)] = (float(x), float(y))
    buses = {b["name"]: b for b in t.get("buses", [])}
    for e in t.get("internal_stations", []):
        if not (e.get("core") and e.get("leg_order") == "along_first" and not e.get("start_core")):
            continue
        bus = e["conn"][4:]
        b, st = buses.get(bus), pins.get(bus, {})
        if b is None or not st or b["face"] != face_want:
            skip.append((tn, bus, e["core"], "face/pins"))
            continue
        nb, (lx, ly) = max(st) + 1, e["leaf_um"]
        d = "in" if str(e.get("launch", "")).startswith("face") else "out"
        if any(abs(IC.length(IC.path(px, py, lx, ly, b["face"], d, IC.column(lo, hi, bit, nb)))
                   - (abs(px - lx) + abs(py - ly))) > 1e-6 for bit, (px, py) in st.items()):
            skip.append((tn, bus, e["core"], "longer"))
            continue
        e["leg_order"], e["channel_um"] = "channel", [lo, hi]
        done[tn] = done.get(tn, 0) + 1
json.dump(raw, open(POUT, "w"), indent=1)
errs = schema.validate(json.load(open(POUT))) or []
print(json.dumps(dict(converted=done, skipped=skip, validate_errors=len(errs), first=errs[:5]), indent=1))
sys.exit(1 if errs else 0)
