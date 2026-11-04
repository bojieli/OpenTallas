#!/usr/bin/env python3
"""DIE-KV-66 11-04: republish the landing collector_tree of the kv3_pc* types moved by RF-KV1/RF-KV3 (same form and guard as
kv65_1103/republish_hub_wi.py; the plan's and the sidecar's copy stay equal). Strict bind before: EMIT collector rst_rl_50:
raw reset parent rst_rl_49 absent.    republish_pc.py PLAN SIDECAR   (repository root)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import reset_tree as RT
import schema

GUARD = ("depth", "own_depth", "entry", "taps", "outs", "n_clock_taps")
# The one named contract change, stated in the READY: the slot shrink leaves this tree one relay shallower (6 -> 5).
ALLOWED = {"kv3_pc__cl254f2e73": {"depth": (6, 5), "own_depth": (6, 5)}}
p, q = Path(sys.argv[1]), Path(sys.argv[2])
raw, side = json.loads(p.read_text()), json.loads(q.read_text())
P = schema.Plan(raw, p)
for tn, t in raw["partition_types"].items():
    if not tn.startswith("kv3_pc"):
        continue
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    old = lc.get("collector_tree")
    if not old:
        continue
    new = json.loads(json.dumps(RT.for_type(P, tn)))
    changed = old != new
    diff = [k for k in GUARD if old.get(k) != new.get(k)
            and ALLOWED.get(tn, {}).get(k) != (old.get(k), new.get(k))]
    print(tn, "changed" if changed else "same", "guard diffs", diff, "relays", len(old.get("relays", [])), len(new.get("relays", [])))
    if diff:
        for k in diff: print("  ", k, str(old.get(k))[:120], "->", str(new.get(k))[:120])
        raise SystemExit(f"{tn}: contract field changed")
    sc = side["collector"]["types"].get(tn)
    if sc is None or sc["tree"] != old:
        raise SystemExit(f"{tn}: sidecar tree differs")
    lc["collector_tree"] = new
    sc["tree"] = new
p.write_text(json.dumps(raw, indent=1) + "\n")
q.write_text(json.dumps(side, indent=1) + "\n")
