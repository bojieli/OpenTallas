#!/usr/bin/env python3
"""DIE-KV-58 10-31 (GEOM-93 r2r, raw-reset part): literal same-depth raw-reset branches (existing FE3
clock.landing_raw_branches) for the count origin and the FSTART face flops of kv3_io_ft / kv3_io_ft_v1 / kv3_hroot.
Their raw reset (cland_start_raw = the first landed input ring's tap relay rst_n_t<k>) sits at the E landing bank, up to
~1300 / ~2000 um from the S-edge origin and the W/S-face FSTART flops (kit r2r u_rrl_5 -> u_cland_origin 979 um,
-> u_cland_fstart_ft1_o 1531 um).  The origin consumer needs clock_landings' START-TREE strap origin to honour the
"origin" raw-branch role (DIE-KV-58 tool line, opt-in).  Each branch copies the ORIGINAL relay chain of that raw reset from the deepest
ancestor that still allows hops <= HOP_UM, at sites on the L path towards the consumer: same clock, same D chain, same
depth -> the same release cycle; +flops only.
Reads the bound type RTL of a strict bind of the plan (relay sites from its '@ (x, y)' comments).
usage: raw_branches_gen.py PLAN.json BIND_RTL_DIR OUT.json"""
import json, math, re, sys

TYPES = ("kv3_io_cor",)
HOP_UM = 330.0
NEED_UM = 0.0           # every consumer gets its own branch: the origin branch re-points cland_start_raw, the
                        # FSTART flops' default, so a near-raw FSTART also needs its own (1-copy) local branch
EDGE_Y = 12.0
INSET = 14.0
REL = re.compile(r"ot_dp_rrelay\s+(\w+)\s*\(\.clk\(clk\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)\);\s*//[^\n]*?depth (\d+) @ \(([-\d.]+), ([-\d.]+)\)")


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def lpath(a, t, n, w):
    tx = min(max(t[0], INSET), w - INSET)
    L1, L2 = abs(tx - a[0]), abs(t[1] - a[1])
    tot = L1 + L2
    pts = []
    for k in range(1, n + 1):
        d = tot * k / (n + 1)
        if d <= L1:
            x, y = a[0] + math.copysign(d, tx - a[0]), a[1]
        else:
            x, y = tx, a[1] + math.copysign(d - L1, t[1] - a[1])
        pts.append([round(x, 3), round(y, 3)])
    return pts


def main():
    plan, rtl_dir, out = sys.argv[1:4]
    P = json.load(open(plan))
    res = {}
    for tn in TYPES:
        text = open(f"{rtl_dir}/{tn}_part.sv").read()
        m = re.search(r"assign cland_start_raw = (\w+);", text)
        raw = m.group(1)
        by_q = {q: dict(inst=i, d=d, depth=int(dep), xy=(float(x), float(y))) for i, d, q, dep, x, y in REL.findall(text)}
        chain = [raw]
        while chain[-1] in by_q and by_q[chain[-1]]["d"] in by_q:
            chain.append(by_q[chain[-1]]["d"])
        chain = chain[::-1]                       # shallowest ... raw
        t = P["partition_types"][tn]
        w, h = t["outline_um"]
        lc = t["clock"]["landing_contract"]
        pins = {p["name"]: p["xy_um"] for p in lc["pins"]}
        sp = pins["cland_tstart_in"]
        cons = {"origin": (sp[0], EDGE_Y)}
        for n, xy in sorted(pins.items()):
            if n.startswith("cland_fstart_out_"):
                cons["fstart:" + n[len("cland_fstart_out_"):]] = tuple(xy)
        src = by_q[raw]["xy"]
        branches, rep = [], {}
        for role, xy in cons.items():
            d0 = man(src, xy)
            if d0 <= NEED_UM:
                rep[role] = dict(direct_um=round(d0, 1), branch=None)
                continue
            best = None
            for k in range(len(chain) - 2, -1, -1):          # deepest base first
                base = chain[k]
                mcopy = len(chain) - 1 - k
                hop = man(by_q[base]["xy"], xy) / (mcopy + 1)
                if hop <= HOP_UM:
                    best = (k, base, mcopy)
                    break
            if best is None:
                k, base, mcopy = 0, chain[0], len(chain) - 1
            else:
                k, base, mcopy = best
            pts = lpath(by_q[base]["xy"], xy, mcopy, w)
            name = "o" if role == "origin" else "fs_" + role.split(":", 1)[1]
            branches.append(dict(name=name, base=base,
                                 stages=[dict(original=chain[k + 1 + i], xy_um=pts[i]) for i in range(mcopy)],
                                 consumers=[role]))
            hops = [man(a, b) for a, b in zip([list(by_q[base]["xy"])] + pts, pts + [list(xy)])]
            rep[role] = dict(direct_um=round(d0, 1), base=base, base_xy=by_q[base]["xy"], copies=mcopy,
                             max_hop_um=round(max(hops), 1))
        res[tn] = dict(raw=raw, raw_xy=src, chain=chain, branches=branches, report=rep)
        print(tn, raw, src, "branches", len(branches), "flops", sum(len(b["stages"]) for b in branches),
              "max hop", max([r.get("max_hop_um", r["direct_um"]) for r in rep.values()]))
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
