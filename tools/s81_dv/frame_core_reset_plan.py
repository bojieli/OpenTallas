#!/usr/bin/env python3
"""frame_core_reset_plan.py -- plan side of frame_band_plan.py (k) (S81-UNBLOCK-1 10-27, COORD RULING S81-KITS-1 C).

Every S81 frame partition type (contents module <m>_l4_lp_r<k>[_nx]) compiles the (k) contents file
rtl/dsrom_sys/s81_dv/frame_lp/plan/<m>_l4_lp_plan_kit_cr.sv instead of <m>_l4_lp_plan_kit.sv, and its r1/r2 band
binds rst_n -> rst_n (the partition's delivered wavefront reset; r0 already did).  Nothing else changes: no pin,
outline, bus, latency or clock edit (the element core's reset release follows the partition wavefront, recorded in
the report as wf_plan core_release).

    python3 tools/s81_dv/frame_core_reset_plan.py PLAN.json OUT.json [--report R.json]
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

BAND = re.compile(r'^(col_h\d+)_l4_lp_r(\d)(_nx)?$')


def apply(raw):
    """-> (raw', log) in place on a deep copy; idempotent."""
    import copy
    raw = copy.deepcopy(raw)
    log = []
    for tn, t in sorted(raw["partition_types"].items()):
        bands = [c for c in t.get("contents", []) if BAND.match(c["module"])]
        if not bands:
            continue
        srcs = t.get("sources", [])
        for i, s in enumerate(srcs):
            m = re.fullmatch(r'(rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h\d+_l4_lp_plan_kit)\.sv', s)
            if m:
                srcs[i] = m.group(1) + "_cr.sv"
                log.append(f"{tn}: source {s} -> {srcs[i]}")
        if not any(s.endswith("_plan_kit_cr.sv") for s in srcs):
            raise SystemExit(f"{tn}: frame type without a plan_kit source {srcs}")
        for c in bands:
            b = c.setdefault("bind", {})
            if b.get("rst_n", "rst_n") != "rst_n":
                raise SystemExit(f"{tn}.{c['inst']}: rst_n bound to {b['rst_n']}")
            if "rst_n" not in b:
                b["rst_n"] = "rst_n"
                log.append(f"{tn}.{c['inst']} ({c['module']}): bind rst_n -> rst_n")
    return raw, log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    src = Path(a.plan).read_bytes()
    raw, log = apply(json.loads(src))
    txt = json.dumps(raw, indent=1) + "\n"
    Path(a.out).write_text(txt)
    rep = dict(tool="tools/s81_dv/frame_core_reset_plan.py", plan=a.plan, plan_sha256=hashlib.sha256(src).hexdigest(),
               out=a.out, out_sha256=hashlib.sha256(txt.encode()).hexdigest(), edits=log,
               types=sorted({x.split(":")[0].split(".")[0] for x in log}))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"frame_core_reset_plan: {len(rep['types'])} types, {len(log)} edits -> {a.out} sha256 {rep['out_sha256'][:10]}")


if __name__ == "__main__":
    sys.exit(main())
