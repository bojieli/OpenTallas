#!/usr/bin/env python3
"""HBM-KITIST-1 11-12: plan-side generator of a `station_trees` entry (kit_istation_forms.py) from a bus's per-core
internal_stations rows.  Trunk = the longest row (its K registers, face -> far core); every other core joins the trunk at
the LAST trunk station m' (1..K) from which its remaining distance fits (K - m' + 1) hops of REACH, and carries the
remaining r = K - m' registers on a branch beside the core: every reader / source is exactly K stations from the face.
Same shape for in buses (face -> cores) and out buses (cores -> face; rows are reversed to face -> core order).

usage: station_tree_plan.py PLAN.json TYPE BUS [OUT_PLAN.json]   -> JSON {entry, stats} on stdout; OUT_PLAN: the plan with the bus's\nrows rewritten to the tree form and the station_trees entry added (run once per bus; plan side of the form)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_bus_bitgroups as BG  # noqa: E402
import kit_istation_forms as KF  # noqa: E402

REACH = 360.0


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _tag(core):
    return "".join(c if c.isalnum() else "_" for c in core)


def plan_tree(rows, in_bus, width, hard=(), reach=REACH):
    """-> dict(entry=<station_trees item without bus>, stats=...).  rows: the bus's internal_stations rows."""
    per = {}
    for e in rows:
        c = BG.core_of_entry(e, hard)
        if c is None or not e.get("from_um") or not e.get("to_um"):
            continue
        path, regs = KF._row_regs(e, in_bus)           # in: face->core ; out: core->face
        if not in_bus:
            path, regs = path[::-1], regs[::-1]       # tree geometry is always face -> core
        cur = per.get(c)
        if cur is None or len(regs) > len(cur["regs"]):
            per[c] = dict(core=c, path=path, regs=regs, bits=int(e.get("bits", 1)), end=path[-1])
        elif cur is not None:
            cur["bits"] += int(e.get("bits", 1))
    if not per:
        raise ValueError("no usable rows")
    k = max(len(v["regs"]) for v in per.values())
    trunk_c = max(per.values(), key=lambda v: (len(v["regs"]), sum(_man(a, b) for a, b in zip(v["path"], v["path"][1:]))))
    trunk = trunk_c["regs"]
    if len(trunk) != k:
        raise ValueError("trunk row shorter than the bus depth")
    nodes = [dict(id=f"t{i}", parent=(f"t{i - 1}" if i else None), site_um=[round(x, 3) for x in trunk[i]]) for i in range(k)]
    atts, viol, extra, hops, geom = [], [], 0, [], {}
    for c, v in sorted(per.items()):
        if c == trunk_c["core"]:
            atts.append(dict(node=f"t{k - 1}", core=c))
            geom[c] = dict(m=k, tap=None, branch=[])
            continue
        placed = False
        for m in range(k, 0, -1):                       # m trunk stations before the branch; r = k - m branch registers
            r = k - m
            d = _man(trunk[m - 1], v["end"])
            if d <= reach * (r + 1):
                parent = f"t{m - 1}"
                prev = parent
                bsites = []
                for j in range(r):
                    f = (j + 1) / (r + 1)
                    x = trunk[m - 1][0] + f * (v["end"][0] - trunk[m - 1][0])
                    y = trunk[m - 1][1] + f * (v["end"][1] - trunk[m - 1][1])
                    nid = f"{_tag(c)}_b{j}"
                    nodes.append(dict(id=nid, parent=prev, site_um=[round(x, 3), round(y, 3)]))
                    bsites.append([round(x, 3), round(y, 3)])
                    prev = nid
                geom[c] = dict(m=m, tap=[round(x, 3) for x in trunk[m - 1]], branch=bsites)
                atts.append(dict(node=prev, core=c))
                extra += r
                hops.append(round(d / (r + 1), 1))
                placed = True
                break
        if not placed:
            viol.append(dict(core=c, dist_um=_man(trunk[0], v["end"]), limit_um=reach * k))
            atts.append(dict(node=f"t{k - 1}", core=c))
            geom[c] = dict(m=k, tap=None, branch=[])
    key = "readers" if in_bus else "sources"
    entry = {"nodes": nodes, key: atts}
    stats = dict(dir="in" if in_bus else "out", k=k, cores=len(per), trunk_core=trunk_c["core"], branch_nodes=extra,
                 data_flops_single_chain_upper=width * k, max_branch_hop_um=max(hops) if hops else 0.0,
                 violations=viol, note="data_flops = width*k + sum(branch nodes * core bits); core bits <= width")
    return dict(entry=entry, stats=stats, geom=geom)


def tree_rows(rows, res, in_bus, hard=()):
    """internal_stations rows of the tree form (same capture groups, rewritten from/regs/to): a branch core's rows run from the
    trunk tap through its branch registers to the core (out bus: core -> branch -> tap); trunk core rows are unchanged"""
    out = []
    for e in rows:
        c = BG.core_of_entry(e, hard)
        g = res["geom"].get(c)
        if g is None or g["tap"] is None:
            out.append(e)
            continue
        face_first = str(e.get("launch", "")).startswith("face bus")
        n = dict(e)
        br = [list(x) for x in g["branch"]]
        if face_first == in_bus or face_first:        # row runs face -> core
            n["from_um"], n["regs_um"], n["to_um"] = list(g["tap"]), br, e["to_um"]
        else:                                         # row runs core -> face
            n["from_um"], n["regs_um"], n["to_um"] = e["from_um"], br[::-1], list(g["tap"])
        n["note"] = (e.get("note", "") + " | HBM-KITIST-1 station tree: tap t%d + %d branch reg(s)" % (g["m"] - 1, len(br))).strip(" |")
        out.append(n)
    return out


def main(argv):
    if len(argv) not in (3, 4):
        raise SystemExit(__doc__)
    raw = json.load(open(argv[0]))
    t = raw["partition_types"][argv[1]]
    b = next(x for x in t["buses"] if x["name"] == argv[2])
    rows = [e for e in t["internal_stations"] if e.get("conn") == "bus:" + argv[2]]
    hard = [h["inst"] for h in t.get("hard_cores", [])]
    out = plan_tree(rows, b["dir"] == "in", b["width"], hard)
    out["entry"]["bus"] = argv[2]
    if len(argv) > 3:                                 # --apply OUT.json: write the plan with the tree rows + station_trees entry
        t["internal_stations"] = [e for e in t["internal_stations"] if e.get("conn") != "bus:" + argv[2]] + \
            tree_rows(rows, out, b["dir"] == "in", hard)
        t.setdefault("station_trees", []).append(out["entry"])
        json.dump(raw, open(argv[3], "w"), indent=1)
    print(json.dumps(dict(stats=out["stats"], entry=out["entry"]), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
