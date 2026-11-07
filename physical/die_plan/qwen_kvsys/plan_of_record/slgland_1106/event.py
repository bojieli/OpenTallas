#!/usr/bin/env python3
"""KV-SLGLAND-1 11-06 (COORD 20:0x (4) fix-only plan event; DIE-KV-84 core-tap ruling): kv3_pv*, kv3_hgi*, kv3_hg* landing re-form.
Why (measured): kv3_pv_v3n GRT (DIE-KV-82 run, epyc5 .../pv_v3n_noid congestion-10.rpt) summed overflow 158,117 at it 10, not
converging; 54% inside the four 1056-bit slg rsp rings (u_cland_i_slg_{W,E}_N_rsp(_d1): S edge x 417-576 + W/E top corners) and
~20% in the plain-tag vport/pvw rings.  Every band of the 35 types carries the plain ring tag (all ring cells FIRM in netlist
order), the class KV-IOCOR-1 fixed on kv3_io_cor/_v1 (433,700 -> 0 GRT overflow, iocorwreg_1106).  Same form here:
(1) ring_place ff on every ring band >= 128 bits (flops FIRM bit-major, ring logic to GPL); fill_axis x when all the bus pins sit
    on the N or S face (FLOW-12 rows=2 face strip, 50% column density; the rows=1 '+ff band as +x' strip left 1.0-1.6k
    overflow on io_cor ft15_i).  Bands with rects_um / ff_rect_um / native_role_banks are left alone (none today).
(2) WREG-1 writer on every ring (clock.landing_ring_wreg {buses: all rings, dsrep 1}; strap K + 1 by bind, 0 data cycles) and the
    private status bank (landing_control_status_copy), so the ff form does not trade congestion for the io_cor_v1 fstart ->
    write-enable broadcast TT setup class (ftwreg_1104, sdwreg_1106, iocorwreg_1106).
(3) clock.core_taps internal -> early (DIE-KV-84 ruling 20:1x from KV-PVTAP-1 kv3_pv_v3n_vB: post-CTS FF -360.25 -> -209.19,
    tap spread 261 -> 148); every one of these types has SIGNED core tap means.  kv3_pc*/kv3_hub* untouched.
No outline, pin, rect or reservation change.  Idempotent.  usage (repo root): event.py PLAN_IN PLAN_OUT"""
import collections, copy, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))
import schema as S, gen_phys as G
TYPES = re.compile(r"^kv3_(pv|hgi|hg)(_|$)")
WIDE = 128
a, b = sys.argv[1:3]
raw = json.load(open(a))
orig = copy.deepcopy(raw)
P = S.Plan(copy.deepcopy(raw), Path(a).resolve())
rep = collections.Counter()
for tn in sorted(raw["partition_types"]):
    if not TYPES.match(tn):
        continue
    t = raw["partition_types"][tn]
    ck = t["clock"]
    faces = collections.defaultdict(set)
    for bus, _bit, _ln, _x, _y, f in G.type_pins(P, tn):
        faces[bus].add(f)
    bands = ck["landing_contract"]["bands"]
    rings = sorted(k for k, v in bands.items() if not k.startswith("monitor_") and v.get("rect_um"))
    for k in rings:
        v = bands[k]
        if v.get("width", 0) < WIDE or any(x in v for x in ("rects_um", "ff_rect_um", "native_role_banks")):
            continue
        v["ring_place"] = "ff"
        rep["ff"] += 1
        if faces.get(k) and faces[k] <= {"N"} or faces.get(k) and faces[k] <= {"S"}:
            v["fill_axis"] = "x"
            rep["x"] += 1
    ck["landing_ring_wreg"] = {"buses": rings, "dsrep": 1}
    t["landing_control_status_copy"] = True
    assert ck.get("core_taps") in ("internal", "early"), (tn, ck.get("core_taps"))
    core = [x for x in ck.get("taps", []) if isinstance(x, dict) and x.get("kind") == "core"]
    assert core and all(str(x.get("budget_owner", "")).startswith("SIGNED:") for x in core), tn
    ck["core_taps"] = "early"
    rep["types"] += 1
for k in raw:
    if k != "partition_types":
        assert raw[k] == orig[k], k
for tn in raw["partition_types"]:
    if not TYPES.match(tn):
        assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
open(b, "w").write(json.dumps(raw, indent=1) + "\n")
print(dict(rep))
