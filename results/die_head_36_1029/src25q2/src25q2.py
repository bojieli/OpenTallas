#!/usr/bin/env python3
"""DIE-HEAD-36 src25q2 (2026-10-29, HEAD-KITS-V 22:14 ASK): src25q put two START raw reset export pins of one type on the
same xy (two relays of one pad chain share a site) -> duplicate M7 pin -> GRT-0080 'Invalid pin placement'.
Fix: every landing pin group sharing (layer, xy) gets distinct M7 track sites nearest the relay (vertical M7 tracks
x = 0.032 + k*0.064 um, the make_tracks grid of the 10-29 hd_mesh_e track snap), |dx| <= one track (0.064 um), y unchanged.
The export ROW keeps the actual relay site (raw-Q/coordinate fixed point unchanged); only the landing pin steps beside it.  Only plan
data changes; RTL is regenerated for the touched types and must be byte-identical.  Report: no-duplicate scan, all types.
usage: src25q2.py ROOT SRC25Q OUT"""
import hashlib, json, math, shutil, sys
from collections import defaultdict
from pathlib import Path
root, src, out = (Path(a).resolve() for a in sys.argv[1:4])
sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
import schema as S, reset_tree as RT, gen_rtl as G, clock_landings as C
from head_start_reset_aliases import patch_rtl
if out.exists(): sys.exit(f"{out} exists")
PITCH, OFF = 0.064, 0.032
raw = json.load(open(src / "source_plan.json"))

def dups(raw):
    res = {}
    for tn, t in sorted(raw["partition_types"].items()):
        g = defaultdict(list)
        for q in t.get("clock", {}).get("landing_contract", {}).get("pins", []):
            g[(q.get("layer"), round(q["xy_um"][0], 4), round(q["xy_um"][1], 4))].append(q["name"])
        d = {f"{k[0]}@{k[1]},{k[2]}": v for k, v in g.items() if len(v) > 1}
        if d: res[tn] = d
    return res

before = dups(raw); moves = []
for tn, d in before.items():
    t = raw["partition_types"][tn]; pins = t["clock"]["landing_contract"]["pins"]
    used = {(q.get("layer"), round(q["xy_um"][0], 4), round(q["xy_um"][1], 4)) for q in pins}
    rows = {r["port"]: r for r in t.get("reset_start_raw_exports", [])}
    for key, names in d.items():
        assert all(n in rows and not rows[n].get("existing_port") for n in names), (tn, names)  # only raw export pins
        layer = key.split("@")[0]; assert layer == "M7", key
        x0, y0 = [float(v) for v in key.split("@")[1].split(",")]
        k0 = (x0 - OFF) / PITCH
        tracks = sorted({round(OFF + PITCH * k, 4) for k in range(math.floor(k0) - 3, math.ceil(k0) + 4)}, key=lambda x: (abs(x - x0), x))
        free = [x for x in tracks if (layer, x, round(y0, 4)) not in used and abs(x - x0) <= PITCH + 1e-9]
        assert len(free) >= len(names), (tn, key, free)
        for n, x in zip(sorted(names), free):
            q = [p for p in pins if p["name"] == n][0]
            q["xy_um"] = [x, y0]; used.add((layer, x, round(y0, 4)))
            moves.append(dict(type=tn, port=n, relay=rows[n]["instance"], from_um=[x0, y0], to_um=[x, y0], dx_um=round(x - x0, 4)))
after = dups(raw)
assert not after, after
assert not S.validate(raw)
shutil.copytree(src, out)
plan = out / "source_plan.json"; plan.write_text(json.dumps(raw, indent=1) + "\n")
P = S.Plan(raw, plan)
# fixed point (relay/Q exact, coordinate <= 0.05 um) on every type
bad = []; n = 0
for tn, t in sorted(P.types.items()):
    rs = t.get("reset_start_raw_exports", [])
    if not rs: continue
    T = RT.for_type(P, tn); rl = RT.start_relays(T) if T.get("start") else T["relays"]; by = {r["name"]: r for r in rl}
    for r in rs:
        a = by.get(r["instance"]); n += 1
        if a is None or a["q"] != r["net"] or max(abs(x - y) for x, y in zip(a["xy"], r["xy_um"])) > .05: bad.append((tn, r["port"]))
side = json.load(open(src / "source_sidecar.json")); L = C.Landings(raw, side); ep = G.bus_epochs(P)
rtl = {}
for tn in sorted(before):
    m = P.types[tn]["module"] + ".sv"
    txt = patch_rtl(L.type_rtl(tn, G.wrapper(P, tn, ep)), P.types[tn].get("reset_start_raw_exports", []))
    rtl[m] = "SAME" if txt == (src / m).read_text() else "DIFF"
rep = dict(source=str(src), duplicates_before=before, duplicates_after=after, moves=moves,
           fixed_point_rows=n, fixed_point_mismatch=bad, rtl_vs_src25q=rtl,
           sha256={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in [plan, out / "source_sidecar.json"]})
(out / "src25q2_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps(rep, indent=1))
if bad or after or "DIFF" in rtl.values(): sys.exit("GATE FAIL")
