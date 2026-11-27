#!/usr/bin/env python3
"""rows_start_settle.py PLAN_IN PLAN_OUT REPORT.json --asbuilt AB.json   (P-STALE-TABLE sub-cause START-SETTLE, QC-R3-TREERTL 11-27)

A row script (row_gate.py --row script:tools/die_plan/rows_start_settle.py::'{in} {out} {report} --asbuilt <rel>') that regenerates the
START boot numbers of the landing sidecar from the bound plan: max wavefront release (reset_tree.wf_plan of PLAN_IN, never a constant),
the collector ready bound (plan_gate_pre.start_settle_bound) and count_aligned.root_settle_cycles = max(recorded, ready bound), in the
sidecar named by the as-built clock_landing_table (written in place in the launch tree; the gate forks the tree first) and in the plan's
clock.landing_network.count_aligned_bind.root_settle_cycles.  The START-SETTLE PRE check (FAIL) then holds for the plan."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def derive(plan_raw, plan_path, side):
    """-> (side', report): side' = copy with the plan-derived release / ready bound / settle"""
    import copy
    import reset_tree as RT
    import schema as S
    import plan_gate_pre as G
    P = S.Plan(plan_raw, plan_path)
    max_release = int(RT.wf_plan(P)["max_release"])
    side = copy.deepcopy(side)
    col = side.get("collector") or {}
    bud = col.get("boot_budget")
    if not bud or not bud.get("local_registered_depths"):
        raise SystemExit("sidecar has no collector boot_budget local_registered_depths")
    old = dict(release=bud.get("raw_reset_release_max_cycles"), ready=bud.get("ready_at_glue_max_cycles"),
               settle=(side.get("count_aligned") or {}).get("root_settle_cycles"))
    bud["raw_reset_release_max_cycles"] = max_release
    col["reset_max_release"] = max_release
    need = int(G.start_settle_bound(side, max_release))
    bud["ready_at_glue_max_cycles"] = need
    ca = side.setdefault("count_aligned", {})
    ca["root_settle_cycles"] = max(int(ca.get("root_settle_cycles") or 64), need)
    return side, dict(old=old, new=dict(release=max_release, ready=need, settle=ca["root_settle_cycles"]))


def apply_plan(raw, settle):
    cb = (((raw.get("clock") or {}).get("landing_network") or {}).get("count_aligned_bind"))
    if isinstance(cb, dict):
        cb["root_settle_cycles"] = settle
        return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("report")
    ap.add_argument("--asbuilt", required=True)
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan_in).read_text())
    ab = json.loads(Path(a.asbuilt).read_text())
    sc = Path(ab["clock_landing_table"])
    if not sc.is_absolute():
        sc = Path.cwd() / sc                       # the row runs in the launch tree; the as-built names a tree-relative path
    side = json.loads(sc.read_text())
    new, rep = derive(raw, a.plan_in, side)
    rep["plan_updated"] = apply_plan(raw, rep["new"]["settle"])
    rep["sidecar"] = str(sc)
    if os.path.islink(sc):
        raise SystemExit(f"{sc} is a symlink; refusing to write through it")
    sc.write_text(json.dumps(new, separators=(",", ":")) + "\n")
    Path(a.plan_out).write_text(json.dumps(raw, separators=(",", ":")) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"rows_start_settle: release {rep['old']['release']} -> {rep['new']['release']}, ready {rep['old']['ready']} -> "
          f"{rep['new']['ready']}, root_settle_cycles {rep['old']['settle']} -> {rep['new']['settle']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
