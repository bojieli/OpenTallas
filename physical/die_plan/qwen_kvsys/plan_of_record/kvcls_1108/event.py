#!/usr/bin/env python3
"""KV-TYPES-4 11-08 kvcls_1108: the KV type class fixes as ONE plan event on main plan_c (OWNER 04:46 "do all the
classes fixes and relaunch").

 C1 LANDING-RING-DENSITY: tools/die_plan/ring_band_spread.py (ring_ff spread 7 on every ring >= 192 bits, all types).
    Run first; its output plan is this script's input.
 C2 SETUP-AT-GRT + FT-CHAIN HOLD on kv3_io_ft_v1 (Codex combined form, codex/kv-start-obstacles-0222 ioft review):
    clock.ft_hop_lockup {"types": ["kv3_io_ft_v1"]} (TYPE-SAFE-1 ot_dp_lk lockup per ft station hop, zero cycles) and
    partition_types.kv3_io_ft_v1.landing_status_reg = true (STATUS-REG per-slot capture, status fault +1 clk, data 0).
 Only those keys change (asserted against the input).

usage (repo root): event.py PLAN_IN PLAN_OUT
"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))
import schema as S  # noqa: E402

IOFT = "kv3_io_ft_v1"
NOTE = ("KV-TYPES-4 11-08 kvcls_1108 C2: TYPE-SAFE-1 hold-safe ft station hops on kv3_io_ft_v1 (SR routed -27.6 on "
        "398 zero-logic station hops), with landing_status_reg (lockup-only GRT TT -50.83 on lap_ok)")


def main(a, b):
    text = open(a).read()
    plan = json.loads(text)
    orig = copy.deepcopy(plan)
    ck = plan.setdefault("clock", {})
    if ck.get("ft_hop_lockup"):
        raise SystemExit(f"base plan already has clock.ft_hop_lockup: {ck['ft_hop_lockup']}")
    ck["ft_hop_lockup"] = {"types": [IOFT], "note": NOTE}
    t = plan["partition_types"][IOFT]
    if t.get("landing_status_reg") is not None:
        raise SystemExit(f"{IOFT} already has landing_status_reg")
    t["landing_status_reg"] = True
    for k in plan:
        if k not in ("clock", "partition_types"):
            assert plan[k] == orig[k], k
    assert {k: v for k, v in plan["clock"].items() if k != "ft_hop_lockup"} == orig.get("clock", {})
    for tn in plan["partition_types"]:
        if tn != IOFT:
            assert plan["partition_types"][tn] == orig["partition_types"][tn], tn
    assert {k: v for k, v in t.items() if k != "landing_status_reg"} == orig["partition_types"][IOFT]
    # splice the two changed objects so every other byte of the file stays as it was
    out = text
    m = re.search(r'^  "' + re.escape(IOFT) + r'": ', out, re.M)
    _, j = json.JSONDecoder().raw_decode(out, m.end())
    out = out[:m.end()] + json.dumps(t, indent=1).replace("\n", "\n  ") + out[j:]
    m = re.search(r'^ "clock": ', out, re.M)
    if m:
        _, j = json.JSONDecoder().raw_decode(out, m.end())
        out = out[:m.end()] + json.dumps(plan["clock"], indent=1).replace("\n", "\n ") + out[j:]
    else:
        out = json.dumps(plan, indent=1) + "\n"
    assert json.loads(out) == plan
    S.Plan(json.loads(out), Path(a).resolve())
    open(b, "w").write(out)
    print("kvcls_1108 C2 applied:", IOFT)


if __name__ == "__main__":
    main(*sys.argv[1:3])
