#!/usr/bin/env python3
"""HBM-REFORM-B3 d44v part 24: ot_hgi_sfu_core_split3__ctl to a smaller tile (74.5k logic, 32k FF, no macros, was spread over 669.6x626.4 at ~8.5% util).
    mk_reform.py PLAN21 PLAN24 tools/die_plan census_empty.json ov_p24.json     outline 427.68x453.6 (pin pitch 0.096: W edge holds 3819 pins)
    mk_p24.py post PLAN24     puts the one clock pin back on the track (hub_repack moves it off the plan lattice), writes part24_event.json
    mk_p24.py recipe RECIPES_SPLIT RECIPES_B2 PINS_SHA    recipes_b2 entry for the module, with the oneclk wrapper pinned to the new pin table"""
import json, sys
from pathlib import Path
CORE = "ot_hgi_sfu_core_split3__ctl"; PINS = CORE + "__427.68x453.6__canon__codex_g21__centry__oneclk.json"
WRAP = "physical/die_plan/hbm_arch_cores/wrappers/oneclk/" + CORE + ".sv"
if sys.argv[1] == "post":
    pd = Path(sys.argv[2]); f = pd / "cores" / PINS; T = json.loads(f.read_text())
    L = T["pins"] if isinstance(T, dict) else T
    c = [p for p in L if p["name"] == "clk"]
    assert len(c) == 1, c
    c[0]["x"], c[0]["y"] = 215.976, 224.64
    f.write_text(json.dumps(T))
    (pd / "part24_event.json").write_text(json.dumps({"schema": "opentallas.hbm_plan_event.part24", "core": CORE,
        "outline": {"from": [669.6, 626.4], "to": [427.68, 453.6]}, "pin_pitch": 0.096, "cycles": "0, RTL unchanged",
        "stations": "regs 180 -> 180, latency_up 0, stations_failed 8 in mk_reform report (advisory, G0 new 0)"}, indent=1) + "\n")
elif sys.argv[1] == "recipe":
    a, b, sha = sys.argv[2:5]; A = json.load(open(a)); B = json.load(open(b))
    e = dict(A[CORE + "__388.8x345.6"]); e["wrapper_by_pins_sha256"] = {sha: WRAP}
    B[CORE] = e
    Path(b).write_text(json.dumps(B, indent=1) + "\n")
