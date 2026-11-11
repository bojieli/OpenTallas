#!/usr/bin/env python3
"""Append route_supply.py results to a FLAGS TSV (PLAN-ROUTE-1; ADVISORY, never a gate).

One row per type and run: flagged yes/no, flagged region + direction, layer, p99 ratio, and the suggested plan change
(street/channel, porous M4/M5 share, outline, ring form).  Rows carry a run stamp and the plan file sha256, so the TSV
is an append-only history: re-run after every plan event; `--changed-only` skips dies whose plan sha is already the
newest one in the TSV.

  route_supply_flags.py OUT_DIR --tsv FLAGS.tsv [--stamp S] [--main SHA] [--plans die=path ...] [--changed-only]
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import sys

HDR = ["stamp", "main", "die", "plan", "plan_sha", "type", "flagged", "region", "dir", "layer", "p99_ratio",
       "ratio_over_threshold", "all_flagged_regions", "suggested_plan_change", "porous_need_free", "provisional_children"]


# routing layers that carry the flagged direction in that region (hard core at the M5 ceiling: M6 H / M7 V only;
# SRAM/ROM blocks M1-M4: M6 H, M5/M7 V; elsewhere all of M2-M7)
LAYER = {("core", "H"): "M6", ("core", "V"): "M7", ("mem", "H"): "M6", ("mem", "V"): "M5/M7",
         ("street", "H"): "M2/M4/M6", ("street", "V"): "M3/M5/M7", ("mstreet", "H"): "M2/M4/M6",
         ("mstreet", "V"): "M3/M5/M7", ("ring", "H"): "M2/M4/M6", ("ring", "V"): "M3/M5/M7",
         ("face", "H"): "M2/M4/M6", ("face", "V"): "M3/M5/M7", ("open", "H"): "M2/M4/M6", ("open", "V"): "M3/M5/M7",
         ("dens", "A"): "M2-M7 (all)"}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def last_shas(tsv):
    out = {}
    if not os.path.exists(tsv):
        return out
    with open(tsv) as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if p[0] == "stamp" or len(p) < 5:
                continue
            out[p[2]] = p[4]
    return out


def suggestion(r):
    if not r.get("flag_regions"):
        return "-", "-"
    reg, d = r["flag_regions"][0][0].rsplit("_", 1)
    s = [r.get("fix", "")]
    nf = "-"
    if reg in ("core", "street"):
        p = (r.get("porous") or {}).get(d) or {}
        if p:
            nf = "none" if p.get("need_free") is None else f"{p['need_free']:.2f}"
            if p.get("need_free") is None:
                s.append(f"porous {p.get('layer')} alone does not cover it (p99 {p.get('p99_all_free')} with all of it free)")
            else:
                s.append(f"or porous abstracts: {p['need_free']:.0%} of blocked {p.get('layer')} over hard cores free")
    if r.get("provisional_children"):
        s.append("re-check after child sign-off (provisional child views)")
    return "; ".join(x for x in s if x), nf


def rows_of(path, stamp, main, plan_sha, plan):
    d = json.load(open(path))
    for r in d["rows"]:
        fl = r.get("flag_regions") or []
        if fl:
            reg, dr = fl[0][0].rsplit("_", 1)
            w = r["worst"]
            layer = LAYER.get((reg, dr)) or (w.get("layer", "") if (w["region"], w["dir"]) == (reg, dr) else "")
            p99 = r["regions"].get(fl[0][0], {}).get("p99", "")
            ratio = fl[0][1]
        else:
            w = r["worst"]
            reg, dr, layer, p99, ratio = w["region"], w["dir"], w.get("layer", ""), w["p99"], "-"
        sug, nf = suggestion(r)
        yield [stamp, main, d["die"], plan, plan_sha, r["type"], "yes" if fl else "no", reg, dr, layer, p99, ratio,
               ",".join(f"{k}:{v}" for k, v in fl) or "-", sug, nf, ",".join(r.get("provisional_children") or []) or "-"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir")
    ap.add_argument("--tsv", required=True)
    ap.add_argument("--stamp", default=datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"))
    ap.add_argument("--main", default="-")
    ap.add_argument("--plans", nargs="*", default=[], help="die=plan_path (for the plan sha column)")
    ap.add_argument("--changed-only", action="store_true")
    a = ap.parse_args(argv)
    plans = dict(p.split("=", 1) for p in a.plans)
    seen = last_shas(a.tsv) if a.changed_only else {}
    new = not os.path.exists(a.tsv)
    n = 0
    with open(a.tsv, "a") as f:
        if new:
            f.write("\t".join(HDR) + "\n")
        for path in sorted(glob.glob(os.path.join(a.out_dir, "route_supply_*.json"))):
            die = json.load(open(path))["die"]
            pp = plans.get(die, "")
            ps = sha(pp) if pp and os.path.exists(pp) else "-"
            if a.changed_only and ps != "-" and seen.get(die) == ps:
                print(f"# {die}: plan {ps} unchanged, skipped", file=sys.stderr)
                continue
            for row in rows_of(path, a.stamp, a.main, ps, os.path.basename(pp) or "-"):
                f.write("\t".join(map(str, row)) + "\n")
                n += 1
    print(f"# appended {n} rows to {a.tsv} (ADVISORY, not a gate)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
