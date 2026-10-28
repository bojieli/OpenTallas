#!/usr/bin/env python3
"""CORES-EARLY-1 10-28: plan pin tables + abstracts of S81 hard cores follow their SIGNED view (plan regeneration input).

Cause (CHECKED 10-28): CORE-VIEWS-1 found dsfd_rstg (2 pins) and ot_s81_sstn_payload536 (all 1074 pins, +-53/54 nm)
MISMATCH between the plan pin table and the signed view.  The plan tables (inputs/core_pins/<m>.json, CORE-KS rule:
centre of the pin's largest non-M1 rect) were cut 10-23 from the pre-ECO planning abstracts
physical/ref_tile/<tile>/views/<m>/<m>.lef, whose pin shapes are deeper (payload536 N/S pins 0.192/0.144 um, rstg
ck[0]/rs[0] with a merged access stub).  The S81-ECO-1 signed views (cea0b97cf, 10-27) were written from the routed
ODB with minimum-depth pin shapes (0.084/0.038 um): same pin, same track, same edge -- only the rect centre the
CORE-KS rule picks moved.  The plan side is stale: the plan must describe the core the die binds (the signed one).

Rule (same generator, no hand edits): for every plan hard core whose module has a published view
physical/die_plan/s81/cores/views/<m>/ with signoff.json verdict SIGNED, re-derive the pin table from the view LEF
unless the kit was cut from the current table (view freeze.json pins_sha256 == table sha256), re-run the plan's own
CORE-KS rule (core_pins_gen.table) on the SIGNED view LEF, keep the table's pin set, and write it only when that pick
equals the view's signed pin table (<view>/pins.json) on every pin (RULE-DIFF otherwise).  Refused (reported, nothing written) when the view SIZE differs
from the plan outline or the signed pin set differs from the plan's -- that is a stale KIT (re-sign needed), not a stale plan
(e.g. ot_s81sl_vq: view signed on the pre-OWNER-DECISION-8 y[255:0] interface, 830 pins vs plan 702).
Where the table changes, hard_cores[].lef/.lib point at the view LEF / _tt.lib.  Tables that already equal the
view's pick are left untouched.

    python3 physical/die_plan/s81/delta_signed_view_pins_1028.py IN.json OUT.json [--write-tables] [--report R.json]
(repo root; without --write-tables only the report is produced)
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
VIEWS = os.path.join("physical", "die_plan", "s81", "cores", "views")
PINS_DIR = os.path.join("physical", "die_plan", "s81")


def _cpg():
    for d in (os.path.join(ROOT, "tools", "die_plan"), HERE):     # core_pins_gen imports schema / gen_plan_v4
        if d not in sys.path:
            sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location("core_pins_gen", os.path.join(HERE, "core_pins_gen.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def view_of(mod, views=VIEWS):
    d = os.path.join(views, mod)
    lef = os.path.join(d, mod + ".lef")
    so = os.path.join(d, "signoff.json")
    if not (os.path.exists(lef) and os.path.exists(so)):
        return None
    try:
        verdict = json.load(open(so)).get("verdict")
    except ValueError:
        return None
    if verdict != "SIGNED":
        return None
    lib = os.path.join(d, mod + "_tt.lib")
    return dict(dir=d, lef=lef, lib=lib if os.path.exists(lib) else None)


def key(p):
    return (p["layer"], round(p["x"], 4), round(p["y"], 4))


def signed_table(view):
    """{name: {name, layer, x, y}} of the kit pin table the view was signed on (<view>/pins.json, run or plan form)"""
    f = os.path.join(view["dir"], "pins.json")
    if not os.path.exists(f):
        return None
    d = json.load(open(f))
    rows = d if isinstance(d, list) else d.get("pins", [])
    out = {}
    for r in rows:
        n = r.get("name") or (r["bus"] if r.get("bit") is None else "%s[%s]" % (r["bus"], r["bit"]))
        out[n] = dict(name=n, layer=r["layer"], x=r["x"], y=r["y"])
    return out


def frozen_sha(view):
    """pins_sha256 of the kit freeze record in the view (the plan table the kit was cut from), else None"""
    f = os.path.join(view["dir"], "freeze.json")
    if not os.path.exists(f):
        return None
    try:
        return json.load(open(f)).get("pins_sha256")
    except ValueError:
        return None


def sha(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def derive(mod, view, table_path, outline, cpg):
    """(status, new_table|None, detail)"""
    cur = json.load(open(table_path))
    if frozen_sha(view) and frozen_sha(view) == sha(table_path):
        return "SAME", None, "kit was cut from this plan table (freeze pins_sha256 == table sha256)"
    new, size = cpg.table(mod, view["lef"])           # the plan's own CORE-KS rule, on the SIGNED abstract
    if outline and tuple(round(v, 3) for v in size) != tuple(round(v, 3) for v in outline):
        return "KIT-STALE", None, "view SIZE %s != plan outline %s" % (list(size), list(outline))
    sig = signed_table(view)
    if sig is None:
        return "NO-PINS", None, "view has no signed pins.json"
    names = [p["name"] for p in cur["pins"]]
    if set(sig) != set(names):
        return "KIT-STALE", None, "signed pin set %d != plan pin set %d (view-only e.g. %s, plan-only e.g. %s)" % (
            len(sig), len(names), sorted(set(sig) - set(names))[:3], sorted(set(names) - set(sig))[:3])
    np_ = {p["name"]: p for p in new["pins"]}
    pins = [np_[n] for n in names]
    off = [n for n in names if key(np_[n]) != key(sig[n])]
    if off:
        return "RULE-DIFF", None, ("CORE-KS pick on the signed LEF differs from the signed pin table on %d pins (e.g. %s):"
                                   " not a stale-abstract case, left for the owner" % (len(off), off[:3]))
    moved = sum(1 for a, b in zip(cur["pins"], pins) if key(a) != key(b))
    if not moved:
        return "FOLLOWS-VIEW", None, "table already equals the CORE-KS pick of the signed view LEF (abstract repointed)"
    out = dict(cur)
    out.update(lef=view["lef"], pinhash=new["pinhash"], pins=pins,
               source="CORES-EARLY-1 10-28: CORE-KS rule (core_pins_gen.table) re-run on the SIGNED view LEF %s "
               "(== its signed pins.json); previous: %s; %d/%d pins moved, pin set unchanged"
               % (view["lef"], cur.get("source", "?"), moved, len(names)))
    return "PLAN-STALE", out, "%d/%d pins moved (CORE-KS pick of the signed LEF == signed pins.json)" % (moved, len(names))


def run(plan, plan_dir, write_tables, views=VIEWS):
    cpg = _cpg()
    rep, done = {}, {}
    for tn, t in plan.get("partition_types", {}).items():
        for h in t.get("hard_cores", []) or []:
            m, pf = h["module"], h.get("pins_file")
            if not pf:
                continue
            v = view_of(m, views)
            if v is None:
                continue
            tp = os.path.join(plan_dir, pf)
            k = (m, pf)
            if k not in done:
                done[k] = derive(m, v, tp, h.get("outline_um"), cpg)
                st, tab, why = done[k]
                rep[m + " | " + pf] = dict(status=st, detail=why, view=v["dir"])
                if st == "PLAN-STALE" and write_tables:
                    with open(tp, "w") as fh:
                        json.dump(tab, fh, indent=0)
            if done[k][0] in ("PLAN-STALE", "FOLLOWS-VIEW"):   # idempotent: a plan read after the tables moved
                h["lef"] = v["lef"]
                if v["lib"]:
                    h["lib"] = v["lib"]
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--write-tables", action="store_true")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    plan = json.load(open(a.inp))
    rep = run(plan, PINS_DIR, a.write_tables)
    json.dump(plan, open(a.out, "w"), indent=1)
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    for k, r in sorted(rep.items()):
        print("%-11s %s: %s" % (r["status"], k, r["detail"]))


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
