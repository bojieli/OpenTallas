#!/usr/bin/env python3
"""S81-TAPROWS 11-15 (FABLE-PD-S81C-0730 decision 1 and 2.3): plan-row deltas on top of the current S81 plan.

The tap of an early core row subtracts what the core was SIGNED against (the frame its IO was closed in, the signed record's
io reference), never the liberty max_clock_tree_path and never an ETM midpoint:

  1. every gb half core (module ..._gb_he / ..._gb_hw): ONE early row on the view's clock pin name at the signed record's
     core_latency.contract.io_reference_ps (tt -> insertion_ps, ff -> insertion_ff_ps); the twin rows (stale pin .ck 437.4 / 476.1,
     liberty max .clk 533.0 / 553.2) are deleted;
  2. bk_sel__t2: clock.insertion_ps 450 + insertion_target_override (as on the col / leaf families), and the early tap of
     dsdv_idx_tx_n32 -> that core's signed reference (insertion_band bound = the vclk the IO was closed against).

usage: s81_taprows.py BASE.json OUT.json --he-record SIGNOFF --hw-record SIGNOFF --idx-record SIGNOFF [--report REPORT.json]
Pure plan edit, no build; deterministic; refuses a row whose reference is missing.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_clock_contract as CC  # noqa: E402

BUDGET = 450
REASON = ("FABLE-PD-S81C-0730: bk_sel__t2 budget 450 (as on the 296 col / leaf types); die common latency stays 250; "
          "the dsdv_idx_tx_n32 tap is its signed reference, not an ETM midpoint")
HALF = {"he": re.compile(r"_gb_he(_tt|_ff)?\.lib$"), "hw": re.compile(r"_gb_hw(_tt|_ff)?\.lib$")}


def _ref(path):
    r = CC.io_reference(json.loads(Path(path).read_text()))
    if r is None:
        raise SystemExit(f"{path}: no io reference (core_latency.contract.io_reference_ps / insertion_band bound)")
    return r


def _row_of(taps, inst):
    return [tp for tp in taps if tp.get("kind") == "core" and (tp["name"] == inst or tp["name"].startswith(inst + "."))]


def apply(plan, refs, root=None, type_name="bk_sel__t2", idx_module="dsdv_idx_tx_n32", budget=BUDGET, bksel=None, bksel_module="dsdv_bksel_q", idx_view=None):
    """edit the plan dict in place; returns the report dict.  One row per half core, on the clock pin name of the core's view
    (LEF / liberty), at the signed reference; the twin rows left by older events (stale pin name, liberty max) are deleted."""
    import cores as C
    rep = dict(halves={"he": 0, "hw": 0}, rows_deleted=0, types=0, half_rows=[], idx=[], type=type_name, budget_ps=budget)
    pins_cache = {}
    for tn, t in plan["partition_types"].items():
        ck = t.get("clock") or {}
        taps = ck.get("taps")
        if not taps:
            continue
        touched = False
        for core in t.get("hard_cores", []) or []:
            h = next((k for k, rx in HALF.items() if rx.search(str(core.get("module", "")) + ".lib")), None)
            if h is None:
                continue
            key = (core.get("lib"), core.get("lef"))
            if key not in pins_cache:
                pins_cache[key] = sorted(C.clock_pins(core, root))
            pins = pins_cache[key]
            if len(pins) != 1:
                raise SystemExit(f"{tn}/{core['inst']}: expected one clock pin in the view, got {pins}")
            want = f"{core['inst']}.{pins[0]}"
            rows = _row_of(taps, core["inst"])
            if not rows:
                continue
            keep = next((r for r in rows if r["name"] == want), None)
            if keep is None:
                keep = rows[0]
                keep["name"] = want
            r = refs[h]
            old = (keep.get("insertion_ps"), keep.get("insertion_ff_ps"))
            keep["insertion_ps"] = round(r["tt"], 2)
            keep["insertion_ff_ps"] = round(r["ff"], 2)
            keep["budget_owner"] = f"signoff.json {r['source']} (signed gb_{h} record)"
            keep["note"] = (f"S81-TAPROWS: one row per half at the signed io reference {r['tt']:g} TT / {r['ff']:g} FF "
                            f"(was {old[0]} TT; FABLE-PD-S81C-0730, FABLE-CLOSURE-STRATEGY lever 3)")
            drop = [x for x in rows if x is not keep]
            for x in drop:
                taps.remove(x)
            rep["rows_deleted"] += len(drop)
            rep["halves"][h] += 1
            touched = True
            if len(rep["half_rows"]) < 4:
                rep["half_rows"].append((tn, keep["name"], old[0], keep["insertion_ps"], keep["insertion_ff_ps"], len(drop)))
        rep["types"] += touched
    t = plan["partition_types"][type_name]
    ck = t["clock"]
    ck["insertion_ps"] = budget
    ck["insertion_target_override"] = {"reason": REASON}
    ck["insertion_ff_ps"] = round(0.81 * budget, 3)      # COORD r104: 450 TT -> 364.5 FF (schema.FF_TT_INSERTION_RATIO), early taps are priced against it
    r = refs["idx"]
    idx_insts = {c["inst"] for c in t.get("hard_cores", []) if c.get("module") == idx_module}
    for tp in ck.get("taps", []):
        if tp.get("kind") != "core":
            continue
        nm = tp["name"]
        if any(nm == i or nm.startswith(i + ".") for i in idx_insts):
            old = (tp.get("insertion_ps"), tp.get("insertion_ff_ps"))
            tp["insertion_ps"] = round(r["tt"], 2)
            tp["insertion_ff_ps"] = round(r["ff"], 2)
            tp["budget_owner"] = f"signoff.json {r['source']} (signed {idx_module} record)"
            tp["note"] = (f"S81-TAPROWS: tap = the signed io reference {r['tt']:g} TT / {r['ff']:g} FF "
                          f"(was {old[0]} / {old[1]}, an ETM midpoint; FABLE-PD-S81C-0730 2.3)")
            rep["idx"].append((nm, old, (tp["insertion_ps"], tp["insertion_ff_ps"])))
    rep["bksel_q"] = []
    if bksel:                                  # FABLE-PD-S81C-0730 s7: bksel_q tap = the b1c reference mean (TT, FF from the same read)
        q_insts = {c["inst"] for c in t.get("hard_cores", []) if c.get("module") == bksel_module}
        for tp in ck.get("taps", []):
            if tp.get("kind") == "core" and any(tp["name"] == i or tp["name"].startswith(i + ".") for i in q_insts):
                old = (tp.get("insertion_ps"), tp.get("insertion_ff_ps"))
                tp["insertion_ps"], tp["insertion_ff_ps"] = round(bksel["tt"], 2), round(bksel["ff"], 2)
                tp["budget_owner"] = f"FABLE-PD-S81C-0730 s7 b1c reference mean ({bksel['basis']})"
                tp["note"] = f"S81-TAPROWS: bksel_q tap = b1c reference {bksel['tt']:g} TT / {bksel['ff']:g} FF (was {old[0]} / {old[1]}, hq3 view)"
                rep["bksel_q"].append((tp["name"], old))
        if not rep["bksel_q"]:
            raise SystemExit("no bksel_q rows")
    rep["idx_view"] = []
    if idx_view:                               # COORD r104: the SIGNED vb lib / lef replace the closed import in the plan core
        for c in t.get("hard_cores", []):
            if c.get("module") == idx_module:
                rep["idx_view"].append((c["inst"], c.get("lef"), c.get("lib")))
                c["lef"], c["lib"] = idx_view["lef"], idx_view["lib"]
        if not rep["idx_view"]:
            raise SystemExit(f"no {idx_module} core in {type_name}")
    if not rep["idx"] or not rep["halves"]["he"] or not rep["halves"]["hw"]:
        raise SystemExit(f"nothing to edit: {rep}")
    plan["note"] = plan.get("note", "") + (f" | S81-TAPROWS: {rep['halves']['he']} he + {rep['halves']['hw']} hw half rows at the signed "
                                           f"reference ({rep['rows_deleted']} twin rows deleted); {type_name} budget {budget}, idx tap at its signed reference")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--he-record", required=True)
    ap.add_argument("--hw-record", required=True)
    ap.add_argument("--idx-record", required=True)
    ap.add_argument("--root", default=".", help="repo root the view paths resolve against")
    ap.add_argument("--bksel-tt", type=float)
    ap.add_argument("--bksel-ff", type=float)
    ap.add_argument("--idx-lef")
    ap.add_argument("--idx-lib")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    refs = {"he": _ref(a.he_record), "hw": _ref(a.hw_record), "idx": _ref(a.idx_record)}
    plan = json.loads(Path(a.base).read_text())
    bk = dict(tt=a.bksel_tt, ff=a.bksel_ff, basis="TT mean read; FF given") if a.bksel_tt and a.bksel_ff else None
    rep = apply(plan, refs, a.root, bksel=bk, idx_view=dict(lef=a.idx_lef, lib=a.idx_lib) if a.idx_lef and a.idx_lib else None)
    Path(a.out).write_text(json.dumps(plan, indent=1))
    rep["refs"] = refs
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
