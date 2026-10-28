#!/usr/bin/env python3
"""FLOW-CLKFREEZE 2026-10-27: BLOCKING clock-net geometry diff around a post-route ECO.

Compares two ot_clk_dump files (tools/die_plan/clk_freeze.tcl) -- 'pre' = the routed DB the ECO starts from,
'post' = the DB after the ECO route (or any intermediate step) -- and FAILs on ANY change of a clock net:
  wire  : the dbWire opcode stream (every point / via / patch rect / term connection) differs; the wire-type bits
          (ROUTED -> FIXED, the freeze itself) are masked, nothing else is;
  pins  : the set of instance pins / ports on the net differs (a buffer was inserted / removed, a sink moved nets);
  inst  : an instance on a clock net changed master, location or orientation;
  net   : a pre clock net is missing after the ECO, or a NEW clock net appeared (a split net).
Exit 0 = PASS (0 changes), 1 = FAIL (net list printed + JSON), 2 = bad input.
FLOW-SHARED-10 2026-10-27 --pre-unrouted: the ECO started from the PRE-DRT (5_1_grt) DB, so no clock net has a wire yet
and the ECO's single detailed route routes the clock for the first time: every pre net must have NO wire (else FAIL),
wires are not compared (nothing was routed to preserve), pins / instances / missing / new nets stay blocking.

  clk_geom_diff.py PRE.tsv POST.tsv [--json OUT.json] [--max-list N] [--pre-unrouted]
"""
import argparse
import json
import sys
from pathlib import Path


def load(path):
    p = Path(path)
    if not p.is_file() or p.stat().st_size == 0:
        raise SystemExit(f"clk_geom_diff: {path} missing or empty")
    nets, pins, insts, missing, header = {}, {}, {}, set(), ""
    for line in p.read_text().splitlines():
        if not line:
            continue
        if line.startswith("#CLKDUMP"):
            header = line
            continue
        f = line.split("\t")
        kind = f[0]
        if kind == "NET":
            # NET name sigtype n_points types tokens
            nets[f[1]] = dict(sig=f[2], length=int(f[3]), types=f[4], tokens=f[5] if len(f) > 5 else "")
        elif kind == "PIN":
            pins[f[1]] = f[2] if len(f) > 2 else ""
        elif kind == "INST":
            insts[f[1]] = dict(master=f[2], x=int(f[3]), y=int(f[4]), orient=f[5], status=f[6] if len(f) > 6 else "")
        elif kind == "MISSING":
            missing.add(f[1])
        else:
            raise SystemExit(f"clk_geom_diff: {path}: unknown record {kind!r}")
    if not header:
        raise SystemExit(f"clk_geom_diff: {path} has no #CLKDUMP header")
    return dict(header=header, nets=nets, pins=pins, insts=insts, missing=missing)


def first_diff(a, b):
    ta, tb = a.split(" "), b.split(" ")
    for i, (x, y) in enumerate(zip(ta, tb)):
        if x != y:
            return dict(op_index=i, pre=x, post=y, pre_ops=len(ta), post_ops=len(tb))
    return dict(op_index=min(len(ta), len(tb)), pre_ops=len(ta), post_ops=len(tb))


def diff(pre, post, pre_unrouted=False):
    out = dict(wire=[], pins=[], inst=[], missing=[], new=[], pre_wired=[], details={})
    for nm, a in sorted(pre["nets"].items()):
        b = post["nets"].get(nm)
        if b is None:
            out["missing"].append(nm)
            continue
        if pre_unrouted:
            if a["length"] or a["tokens"]:
                out["pre_wired"].append(nm)     # a pre-DRT ECO start must not carry any clock wire
        elif a["tokens"] != b["tokens"]:
            out["wire"].append(nm)
            d = first_diff(a["tokens"], b["tokens"])
            d.update(points_pre=a["length"], points_post=b["length"])
            out["details"][nm] = d
        if pre["pins"].get(nm) != post["pins"].get(nm):
            out["pins"].append(nm)
    out["new"] = sorted(set(post["nets"]) - set(pre["nets"]))
    for nm, a in sorted(pre["insts"].items()):
        b = post["insts"].get(nm)
        if b is None or any(a[k] != b[k] for k in ("master", "x", "y", "orient")):
            out["inst"].append(nm)
            out["details"]["INST " + nm] = dict(pre=a, post=b)
    n_changed = len(set(out["wire"]) | set(out["pins"]) | set(out["missing"]) | set(out["new"]) | set(out["pre_wired"]))
    out["mode"] = "pre_unrouted" if pre_unrouted else "routed"
    out["n_nets_pre"] = len(pre["nets"])
    out["n_nets_post"] = len(post["nets"])
    out["n_insts_pre"] = len(pre["insts"])
    out["n_nets_changed"] = n_changed
    out["n_insts_changed"] = len(out["inst"])
    out["fixed_nets_post"] = sum(1 for v in post["nets"].values() if v["types"] == "64")
    out["verdict"] = "PASS" if n_changed == 0 and not out["inst"] else "FAIL"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pre")
    ap.add_argument("post")
    ap.add_argument("--json")
    ap.add_argument("--max-list", type=int, default=40)
    ap.add_argument("--pre-unrouted", action="store_true",
                    help="ECO started pre-DRT: pre clock nets must be wireless; wires not compared (pins/insts still are)")
    a = ap.parse_args(argv)
    try:
        pre, post = load(a.pre), load(a.post)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2
    r = diff(pre, post, a.pre_unrouted)
    r.update(pre=str(a.pre), post=str(a.post), pre_header=pre["header"], post_header=post["header"])
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    m = a.max_list
    print(f"CLK_GEOM_DIFF {r['verdict']} clock nets {r['n_nets_pre']} -> {r['n_nets_post']}: changed {r['n_nets_changed']} "
          f"(wire {len(r['wire'])}, pins {len(r['pins'])}, missing {len(r['missing'])}, new {len(r['new'])}); "
          f"instances on clock nets {r['n_insts_pre']}: changed {r['n_insts_changed']}; FIXED-wired after {r['fixed_nets_post']}"
          + ("; pre-DRT start: wires routed once by the ECO route, not compared" if a.pre_unrouted else ""))
    for k in ("wire", "pins", "missing", "new", "pre_wired", "inst"):
        if r[k]:
            print(f"CLK_GEOM_DIFF {k} ({len(r[k])}): " + " ".join(r[k][:m]) + (" ..." if len(r[k]) > m else ""))
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
