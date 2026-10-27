#!/usr/bin/env python3
"""which routed-net property explains the GRT->RCX stage change? (data only; per unique net, nets >= 20 um)"""
import json, sys, math
def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)
for kit in sys.argv[1:]:
    vc = json.load(open(f"{kit}/via_census.json")); best = {}
    for x in vc:
        if "spef" in x and x["len_um"] >= 20:
            best.setdefault(x["net"], []).append(x["d_stage"])
    nets = {x["net"]: x for x in vc if x["net"] in best and "spef" in x}
    d = [sum(best[n]) / len(best[n]) for n in nets]
    for k, f in [("vias", lambda x: x["vias"]), ("vias/um", lambda x: x["vias_per_um"]), ("Rtot", lambda x: x["spef"]["r"]),
                 ("Ccoup fF", lambda x: x["spef"]["cc"]), ("Ccoup/um", lambda x: x["spef"]["cc"] / x["len_um"]),
                 ("Ctot/um", lambda x: x["spef"]["ctot"] / x["len_um"]), ("len", lambda x: x["len_um"])]:
        print("%-28s n=%2d corr(d_stage, %-9s) = %+.2f" % (kit.split("/")[-1], len(d), k, corr(d, [f(nets[n]) for n in nets])))
