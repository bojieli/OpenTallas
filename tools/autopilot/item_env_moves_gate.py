#!/usr/bin/env python3
"""MOVES-GATE-1122 (COORD to FAM-S81-COL-H9R0-R4: all 4 J7 col_h9_r0_p1 kits died at gen on 'OT_MACRO_MOVES overlap
u_r0.u_c3_6 / u_r0.u_e3.u_e'): check every type's kit_wave item_env OT_MACRO_MOVES against the bound plan BEFORE launch.

The moves row is per item (exact key, or a family glob such as col_h9_r0_p1__t1__pv*), but the plan it was written for can
move on: a later plan event re-placed u_e3 (split into u_e3.u_w / u_e3.u_e), and the stale move then pushed the group onto
u_r0.u_c3_6.  gen refuses that only hours later, per kit.  This gate resolves each plan type's env exactly as run-item does
(kit_wave.item_env: die_gen_env + globs + exact key) and runs gen_phys.macro_move_table (the same outline + overlap check
gen applies) on the type, so a stale row fails here in seconds for the whole die.

  python3 -I tools/autopilot/item_env_moves_gate.py --config ~/coord/autopilot/kit_wave.json --die s81 --plan PLAN.json [--prefix col_h9_r0_p1]
  python3 -I tools/autopilot/item_env_moves_gate.py ... --moves 'col_h9_r0_p1__t1__pv*=u_r0.u_e1:596.16:216.0,...'   (a proposed row)
exit 0 = every checked type passes, 1 = at least one FAIL line, 2 = bad input.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "die_plan"))

import kit_wave as K  # noqa: E402
import gen_phys as G  # noqa: E402


def plan_types(plan):
    """{type name: type dict} of a die plan (partition_types as a dict or a list of named types)"""
    pt = plan.get("partition_types") or {}
    if isinstance(pt, dict):
        return {str(k): v for k, v in pt.items() if isinstance(v, dict)}
    return {str(t.get("name")): t for t in pt if isinstance(t, dict) and t.get("name")}


def check(die_cfg, types, prefix=""):
    """-> [(type, verdict, detail)]: verdict PASS / FAIL for every type that has hard cores and an OT_MACRO_MOVES env"""
    rows = []
    for tn in sorted(types):
        if prefix and not tn.startswith(prefix):
            continue
        t = types[tn]
        if not t.get("hard_cores") or not t.get("outline_um"):
            continue
        try:
            env = K.item_env(die_cfg, tn)
        except ValueError as e:
            rows.append((tn, "FAIL", f"item_env: {e}"))
            continue
        if not env.get("OT_MACRO_MOVES"):
            continue
        try:
            G.macro_move_table(t, tn, {"OT_MACRO_MOVES": env["OT_MACRO_MOVES"]})
            rows.append((tn, "PASS", env["OT_MACRO_MOVES"]))
        except (ValueError, KeyError) as e:
            rows.append((tn, "FAIL", str(e)))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", required=True, help="kit_wave.json")
    ap.add_argument("--die", required=True)
    ap.add_argument("--plan", required=True, help="the bound die plan json")
    ap.add_argument("--prefix", default="", help="only types whose name starts with this")
    ap.add_argument("--moves", action="append", default=[], help="KEY=VALUE: a proposed item_env OT_MACRO_MOVES row (repeatable)")
    a = ap.parse_args(argv)
    try:
        die_cfg = json.load(open(a.config))["dies"][a.die]
        types = plan_types(json.load(open(a.plan)))
    except (OSError, ValueError, KeyError) as e:
        print(f"MOVES-GATE BAD-INPUT {e}")
        return 2
    die_cfg = dict(die_cfg)
    ie = {k: dict(v or {}) for k, v in (die_cfg.get("item_env") or {}).items()}
    for m in a.moves:
        k, _, v = m.partition("=")
        ie.setdefault(k, {})["OT_MACRO_MOVES"] = v
    die_cfg["item_env"] = ie
    rows = check(die_cfg, types, a.prefix)
    for tn, verdict, detail in rows:
        print(f"MOVES-GATE {verdict} {tn}: {detail}")
    bad = sum(1 for r in rows if r[1] == "FAIL")
    print(f"MOVES-GATE {'FAIL' if bad else 'PASS'} {len(rows)} type(s) with OT_MACRO_MOVES checked, {bad} fail")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
