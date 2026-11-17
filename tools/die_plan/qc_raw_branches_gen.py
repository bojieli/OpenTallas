#!/usr/bin/env python3
"""QC-CBGLUE-1116: literal same-depth raw-reset branches (clock.landing_raw_branches, FE3) for the FSTART face flops of
any die's types, generalised from DIE-KV-58 geom96_1031/raw_branches_gen.py.

Measured class (QC cb/glue, post-CTS TT GRT RC): u_cland_fstart_<b> takes rst_raw_n = cland_start_raw, the count
origin's raw reset (the first landed input's ring relay u_cland_rst_<in> or a tap relay u_rrl_<k>) on the far face of
the type: glue u_rrl_257 -> u_cland_fstart_* 1670 um (-492 ps), cbf_q01 u_cland_rst_a00_i -> u_cland_fstart_a00_o
2330 um (-1916 ps), cbf_q01_s2 -> u_cland_fstart_y_o12 (-3020 ps).

For every FSTART face flop whose raw source is more than --need um away, one branch copies the ORIGINAL relay chain of
that raw reset from the deepest ancestor that still allows hops <= --hop um, at sites on the L path towards the
FSTART pin: same clock, same D chain, same depth -> the same release cycle; +flops only, 0 added cycles.

Inputs: the plan (partition_types[tn].clock.landing_contract.pins, outline_um) and the bound RTL of a strict bind of
that plan (relay sites from the '@ (x, y)' comments; the ring relay u_cland_rst_<b> takes the landing pin site of
fclk_in_<b>, where the landing emitter places it).
usage: qc_raw_branches_gen.py PLAN.json BIND_RTL_DIR OUT.json --types T [T ...] [--hop 330] [--need 300]"""
import argparse
import glob
import json
import math
import os
import re
import sys

RELAY = re.compile(r"ot_dp_rrelay\s+(\w+)\s*\(\s*\.clk\(clk\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)\s*\);([^\n]*)")
SITE = re.compile(r"@ \(([-\d.]+), ([-\d.]+)\)")
INSET = 14.0


class GenError(ValueError):
    pass


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def lpath(a, t, n, w, h):
    """n sites evenly spaced on the x-then-y L path a -> t, clamped INSET inside the outline."""
    tx = min(max(t[0], INSET), w - INSET)
    ty = min(max(t[1], INSET), h - INSET)
    L1, L2 = abs(tx - a[0]), abs(ty - a[1])
    tot = L1 + L2
    pts = []
    for k in range(1, n + 1):
        d = tot * k / (n + 1)
        if d <= L1:
            x, y = a[0] + math.copysign(d, tx - a[0]), a[1]
        else:
            x, y = tx, a[1] + math.copysign(d - L1, ty - a[1])
        pts.append([round(x, 3), round(y, 3)])
    return pts


def type_rtl(rtl_dir, tn):
    """The one bound file of type tn that carries the count origin's raw reset."""
    hits = []
    for f in sorted(glob.glob(os.path.join(rtl_dir, "*.sv"))):
        b = os.path.basename(f)
        if not (b == f"{tn}_part.sv" or f"__{tn}_" in b or b.endswith(f"__{tn}.sv") or b == f"{tn}.sv"):
            continue
        if re.search(r"\bassign\s+cland_start_raw\s*=", open(f).read()):
            hits.append(f)
    if len(hits) != 1:
        raise GenError(f"{tn}: expected one bound RTL file with cland_start_raw in {rtl_dir}, found {hits}")
    return hits[0]


def relays(text, pins):
    by_q = {}
    for inst, d, q, comment in RELAY.findall(text):
        if q in by_q:
            raise GenError(f"raw relay Q {q} driven twice")
        m = SITE.search(comment)
        xy = (float(m.group(1)), float(m.group(2))) if m else None
        ring = re.fullmatch(r"u_cland_rst_(\w+)", inst)
        if xy is None and ring and f"fclk_in_{ring.group(1)}" in pins:
            xy = tuple(pins[f"fclk_in_{ring.group(1)}"])
        by_q[q] = dict(inst=inst, d=d, xy=xy)
    return by_q


def gen_type(plan, rtl_dir, tn, hop_um, need_um):
    if tn not in plan.get("partition_types", {}):
        raise GenError(f"{tn}: not a partition type of the plan")
    t = plan["partition_types"][tn]
    w, h = t["outline_um"]
    lc = t.get("clock", {}).get("landing_contract") or {}
    pins = {p["name"]: p["xy_um"] for p in lc.get("pins", [])}
    text = open(type_rtl(rtl_dir, tn)).read()
    raw = re.search(r"\bassign\s+cland_start_raw\s*=\s*(\w+)\s*;", text).group(1)
    by_q = relays(text, pins)
    if raw not in by_q or by_q[raw]["xy"] is None:
        raise GenError(f"{tn}: raw reset {raw} is not a sited plain relay Q")
    chain = [raw]
    while by_q[chain[-1]]["d"] in by_q:
        chain.append(by_q[chain[-1]]["d"])
    chain = chain[::-1]                                     # shallowest ... raw
    src = by_q[raw]["xy"]
    branches, rep = [], {}
    for n in sorted(pins):
        if not n.startswith("cland_fstart_out_"):
            continue
        b = n[len("cland_fstart_out_"):]
        if not re.search(r"\bot_dp_landing_relay\s+u_cland_fstart_" + re.escape(b) + r"\s*\(", text):
            continue                                         # no FSTART face flop: the role would stay unused
        xy = tuple(pins[n])
        d0 = man(src, xy)
        if d0 <= need_um:
            rep[f"fstart:{b}"] = dict(direct_um=round(d0, 1), branch=None)
            continue
        best = None
        for k in range(len(chain) - 2, -1, -1):              # deepest sited base first
            base_xy = by_q[chain[k]]["xy"]
            if base_xy is None:
                continue
            mcopy = len(chain) - 1 - k
            if man(base_xy, xy) / (mcopy + 1) <= hop_um:
                best = k
                break
        if best is None:                                     # shallowest sited ancestor
            best = next((k for k in range(len(chain) - 1) if by_q[chain[k]]["xy"] is not None), None)
            if best is None:
                raise GenError(f"{tn}: no sited ancestor of {raw}")
        k = best
        base = chain[k]
        mcopy = len(chain) - 1 - k
        pts = lpath(by_q[base]["xy"], xy, mcopy, w, h)
        branches.append(dict(name="fs_" + b, base=base,
                             stages=[dict(original=chain[k + 1 + i], xy_um=pts[i]) for i in range(mcopy)],
                             consumers=[f"fstart:{b}"]))
        hops = [man(a, c) for a, c in zip([list(by_q[base]["xy"])] + pts, pts + [list(xy)])]
        rep[f"fstart:{b}"] = dict(direct_um=round(d0, 1), base=base, base_xy=list(by_q[base]["xy"]), copies=mcopy,
                                  max_hop_um=round(max(hops), 1))
    return dict(raw=raw, raw_xy=list(src), chain=chain, branches=branches, report=rep)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("rtl_dir")
    ap.add_argument("out")
    ap.add_argument("--types", nargs="+", required=True)
    ap.add_argument("--hop", type=float, default=330.0)
    ap.add_argument("--need", type=float, default=300.0)
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    res = {}
    for tn in a.types:
        r = gen_type(plan, a.rtl_dir, tn, a.hop, a.need)
        res[tn] = r
        hops = [v.get("max_hop_um", v["direct_um"]) for v in r["report"].values()]
        print(tn, r["raw"], r["raw_xy"], "branches", len(r["branches"]),
              "flops", sum(len(b["stages"]) for b in r["branches"]), "max hop", max(hops) if hops else None)
    json.dump(res, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
