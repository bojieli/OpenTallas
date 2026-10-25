#!/usr/bin/env python3
"""PATH-S81/COLL 10-25 (COORD 10:32 option A WITHDRAWN -> RE-DECIDED: bind tool fix + small C<->LP control lanes).

The strict bind v10b read 14,469 unplanned bits lk_* -> s_{0,7}{N,S}_C -> *_LP.  Cause: the lep slice top's
'assign lrxK = {rxK[512], rxK[513], rxK[511:0], nKrxv}' (and the 1-b reset / valid wires beside it) are anonymous
bit-preserving glue cells that the as-built map put with the slice top (C).  bind.py asbuilt.glue_follows_sinks
(opt-in) moves such pure pass-through glue to the partition of its loads (LP), so the 28 coll__* lanes bind as
planned (unused 12 -> 0) and no lane changes.  What is left is REAL C -> LP traffic beyond the planned kd (1104 b) +
lepf (1 b): 2 b per lep slice (slice ro top bits / u_hbc.next_ro[1103] + u_sl fault).  This delta adds ONE 2-b C -> LP
control lane per lep slice on the shared C|LP face (C type W face / LP type E face, next free window), 0 stations,
latency 2 (boundary pair) like lepf.

    python3 physical/die_plan/s81/delta_coll_1025.py PLAN [OUT]
    python3 physical/die_plan/s81/delta_coll_1025.py --reformat PLAN   (after gen.py latency --inplace: main's format)
"""
import copy
import json
import re
import sys

COMPACT = {"ft_slots", "contents", "hard_cores"}
def dumps_plan(P, compact=None):
    """the S81 main plan's format: indent=1 with every element of the COMPACT keys' lists on one compact line"""
    compact = COMPACT if compact is None else compact
    marks = {}
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in compact and isinstance(v, list):
                    for i, e in enumerate(v):
                        key = "@@C%d@@" % len(marks)
                        marks[key] = json.dumps(e, separators=(",", ":"))
                        v[i] = key
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    Q = copy.deepcopy(P)
    walk(Q)
    return re.sub(r'"(@@C\d+@@)"', lambda m: marks[m.group(1)], json.dumps(Q, indent=1)) + "\n"


SLICES = ("s_0N", "s_0S", "s_7N", "s_7S")
BITS = 2          # residual C -> LP bits per lep slice (bind proof out_b, PATH-S81/COLL 10-25)
GAP = 1.188       # same gap as between the existing kd / ku / flt / lepf windows
MIN_W = 15.14     # the 1-b lepf window


def main(argv):
    if argv[1] == "--reformat":
        P = json.load(open(argv[2]))
        open(argv[2], "w").write(dumps_plan(P))
        return
    src = argv[1]
    out = argv[2] if len(argv) > 2 else src
    P = json.load(open(src))
    PT = P["partition_types"]
    parts = {x["name"]: x for x in P["partitions"]}
    ntype = {}
    for x in P["partitions"]:
        ntype[x["type"]] = ntype.get(x["type"], 0) + 1
    lane_ids = {L["id"] for L in P["lanes"]}
    for hn in SLICES:
        c, lp = parts[hn + "_C"], parts[hn + "_LP"]
        assert c["origin_um"][1] == lp["origin_um"][1], hn
        assert ntype[c["type"]] == 1 and ntype[lp["type"]] == 1, (hn, "C / LP type is shared")
        # C|LP shared face: C type W, LP type E for R0 (LP west of C) and MY (LP east of C, mirrored) alike
        assert (c["orient"], lp["orient"]) in (("R0", "R0"), ("MY", "MY")), hn
        die_face = "W" if c["orient"] == "R0" else "E"          # the C (source) side, as the existing lepf port
        tc, tl = PT[c["type"]], PT[lp["type"]]
        name = "lpc"
        lid = "%s__%s__%s" % (name, c["name"], lp["name"])
        assert lid not in lane_ids, lid
        used = [b["window_um"] for b in tc["buses"] if b["face"] == "W"] + \
               [b["window_um"] for b in tl["buses"] if b["face"] == "E"]
        lo = round(max(w[1] for w in used) + GAP, 3)
        hi = round(lo + max(MIN_W, BITS / 4.6 + 1.0), 3)
        assert hi < tc["outline_um"][1] - 6.0
        for w in used:
            assert hi <= w[0] or lo >= w[1], (hn, w)
        lay = next(b for b in tc["buses"] if b["name"] == "lepf_o0")["layers"]
        tc["buses"].append(dict(name=name + "_o0", dir="out", width=BITS, kind="ctl", face="W", window_um=[lo, hi],
                                layers=list(lay), order="lsb_low"))
        tl["buses"].append(dict(name=name + "_i0", dir="in", width=BITS, kind="ctl", face="E", window_um=[lo, hi],
                                layers=list(lay), order="lsb_low"))
        y0 = c["origin_um"][1]
        pid = lid + "__0"
        P["ports"].append(dict(id=pid, src=dict(part=c["name"], bus=name + "_o0"), dst=dict(part=lp["name"], bus=name + "_i0"),
                               width=BITS, kind="ctl", face=die_face, layers=list(lay),
                               window_um=[round(y0 + lo, 3), round(y0 + hi, 3)], order="lsb_low"))
        P["lanes"].append(dict(id=lid, ports=[pid]))
        P.setdefault("latency", {}).setdefault("lanes", {})[lid] = dict(
            cycles=2, stations=0, boundary=2, faces=1, fixed=0, natural=2, pad=0, param="LAT_" + lid.upper())
        print("%s: +%s %d b C -> LP, type window [%.3f, %.3f] (C %s W / LP %s E)" % (hn, lid, BITS, lo, hi, c["type"], lp["type"]))
    open(out, "w").write(dumps_plan(P))


if __name__ == "__main__":
    main(sys.argv)
