#!/usr/bin/env python3
"""DIE-KV-28 event27 FINAL = DIE-KV-27 plan_e27 (event26a + ASK-C) + Codex native START/reset pin sites
(codex-kv-25-1029 point_native_pins.py -> event26/plan_native_pins.json). COORD 10-29 ruling (a): YES as gate-failure fix
(331 START hops 582..3213 um broke the 405 um leg rule with the old cland_tstart pins).
Overlay is exact: for every partition type, the 3 START/reset landing_contract pins (cland_tstart_in/out, cland_raw_reset_out)
take xy_um/layer/native_entry_reference_um from plan_native_pins; kv3_astk hard cores take the scalar-ABI astk_index0 pins file.
Asserts that event26 (Codex base) and plan_e27 agree on every overlaid field before the overlay (no hidden plan drift).
usage: mk_event27_np.py PLAN_E27 EVENT26_PLAN PLAN_NATIVE_PINS OUT_PLAN"""
import json, sys, hashlib
from pathlib import Path
e27p, e26p, npp, outp = map(Path, sys.argv[1:5])
E27 = json.loads(e27p.read_bytes()); E26 = json.load(open(e26p)); NP = json.load(open(npp))
ROLES = ("cland_tstart_in", "cland_tstart_out", "cland_raw_reset_out")
moved = 0; types = 0; astk = 0; shifts = []
for tn, t in E27["partition_types"].items():
    lc = t.get("clock", {}).get("landing_contract", {}).get("pins", [])
    lc26 = {q["name"]: q for q in E26["partition_types"][tn].get("clock", {}).get("landing_contract", {}).get("pins", [])}
    lcnp = {q["name"]: q for q in NP["partition_types"][tn].get("clock", {}).get("landing_contract", {}).get("pins", [])}
    hit = 0
    for p in lc:
        if p["name"] not in ROLES: 
            assert p == lc26[p["name"]], (tn, p["name"], "non-START landing pin drift")
            continue
        assert p == lc26[p["name"]], (tn, p["name"], "base drift e27 vs event26")
        n = lcnp[p["name"]]
        shifts.append(abs(p["xy_um"][0] - n["xy_um"][0]) + abs(p["xy_um"][1] - n["xy_um"][1]))
        p.update(xy_um=n["xy_um"], layer=n["layer"], native_entry_reference_um=n["native_entry_reference_um"],
                 note=(p.get("note", "") + " | DIE-KV-28 event27: Codex native START pin site (point_native_pins)").lstrip(" |"))
        moved += 1; hit = 1
    types += hit
    for h, h26, hnp in zip(t.get("hard_cores", []), E26["partition_types"][tn].get("hard_cores", []), NP["partition_types"][tn].get("hard_cores", [])):
        if h["module"] == "kv3_astk":
            assert h["pins_file"] == h26["pins_file"], (tn, "astk base drift")
            h["pins_file"] = hnp["pins_file"]; astk += 1
E27["note"] = E27.get("note", "") + " | DIE-KV-28 event27 FINAL: + Codex native START/reset pin sites (COORD 10-29 (a), gate-failure fix 405 um leg rule)"
outp.write_text(json.dumps(E27, indent=1))
print(json.dumps(dict(e27_sha256=hashlib.sha256(e27p.read_bytes()).hexdigest(), np_sha256=hashlib.sha256(npp.read_bytes()).hexdigest(),
                      types_with_start_pins=types, pins_moved=moved, astk_cores=astk, max_shift_um=round(max(shifts), 3),
                      out_sha256=hashlib.sha256(outp.read_bytes()).hexdigest())))
