#!/usr/bin/env python3
"""LF-CS-GATE (S81-LEAF-FLOOR-2 11-12): plan station depth per (leaf type, link class) == bound RTL depth.

The plan's core<->core internal_stations of an S81 leaf type (ot_s81sl_leaf / kv_leaf partitions) are realised in the
RTL as the leaf's station chains u_cst_<class> (ot_s81sl_leaf CS_<CLASS>_D; h trees in ot_s81sl_vp).  The class of a
plan row is kit_istations.core_class (CORE_CLASSES, the map the kit flow sites the stages with); the plan depth of a
class is the deepest row of that class (one interface = one chain); the bound depth is kit_istations.native_params on
the bound partition module (stage registers counted).  Mismatch in either direction is an error: a plan register the
RTL lacks makes the plan's reach limits fiction; an RTL register the plan lacks is an unplanned cycle.
cs (vn_a -> vn_b c_s) rows have no RTL realisation (kit_istations: re-plan vn_a / vn_b within reach): reported as errors.

    leaf_cs_depth.py PLAN.json BOUND_RTL_DIR [--types a,b] [--json OUT]     exit 1 on any mismatch

bind.py calls check() after emit when the as-built manifest sets "leaf_cs_depth_gate": true (errors -> B.errors, so a
--strict bind fails)."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_istations as KI   # noqa: E402

LEAF_TYPE = re.compile(r"^ot_s81sl_(kv_)?leaf__")


def plan_depths(t):
    """{class: deepest planned stage count}, {class: sorted distinct counts} where the rows of a class disagree."""
    rows = {}
    for e in t.get("internal_stations") or []:
        if str(e.get("conn", "")).startswith("bus:"):
            continue
        c, _, _ = KI.core_class(e)
        if c is None:
            continue
        rows.setdefault(c, []).append(len(e.get("regs_um") or []))
    return {c: max(v) for c, v in rows.items()}, {c: sorted(set(v)) for c, v in rows.items() if len(set(v)) > 1}


def bound_depths(txt):
    have = KI.native_params(txt)
    return {c: int(have.get(KI.CLASS_PARAM[c], 0)) for c in KI.CLASS_PARAM}


def bound_file(rtl_dir, tn):
    for n in ("s81p_%s.sv" % tn, "%s.sv" % tn):
        f = Path(rtl_dir) / n
        if f.is_file():
            return f
    return None


def check(plan, rtl_dir, types=None):
    """-> (errors [str], rows [dict]) over the leaf types of the plan (or `types`)."""
    PT = plan["partition_types"]
    errors, rows = [], []
    for tn in sorted(types or [t for t in PT if LEAF_TYPE.match(t)]):
        t = PT.get(tn)
        if t is None:
            errors.append(f"LF_CS_DEPTH {tn}: not a plan type")
            continue
        if not t.get("hard_cores"):
            continue                                   # e.g. kv_leaf__t2: no leaf cores, no chains
        f = bound_file(rtl_dir, tn)
        if f is None:
            errors.append(f"LF_CS_DEPTH {tn}: no bound module file in {rtl_dir}")
            continue
        want, dis = plan_depths(t)
        have = bound_depths(f.read_text())
        for c in sorted(set(want) | {c for c, v in have.items() if v}):
            p, b = want.get(c, 0), have.get(c, 0) if c != "cs" else 0
            row = dict(type=tn, cls=c, plan=p, bound=b, disagree=dis.get(c))
            rows.append(row)
            if c == "cs" and p:
                errors.append(f"LF_CS_DEPTH {tn} cs: {p} planned vn_a->vn_b c_s station(s), no RTL realises them "
                              "(re-plan vn_a / vn_b within reach)")
            elif p != b:
                errors.append(f"LF_CS_DEPTH {tn} {c}: plan {p} stage(s) (deepest row), bound RTL {b}")
    return errors, rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("rtl_dir")
    ap.add_argument("--types", default="")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    errors, rows = check(plan, a.rtl_dir, [t for t in a.types.split(",") if t] or None)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(errors=errors, rows=rows), indent=1))
    for e in errors[:200]:
        print(e)
    print("LF_CS_DEPTH %s: %d mismatch(es) over %d (type, class) rows" % ("FAIL" if errors else "PASS", len(errors), len(rows)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
