#!/usr/bin/env python3
"""TYPE-SAFE-2-AREA 11-08: die-side cost of growing slots on an ABUTTED lattice die (S81: 22 x 20 cells).

Input: a plan and a per-type growth table (ts_area.py JSON: types[].outline / new_outline).
Reports three numbers per axis (never a gate):
  row_sum   : max over die rows (columns) of the summed growth, gaps kept (the optimistic figure that ignores the
              shared-face alignment of abutted neighbours)
  lattice   : per lattice column dx = max growth of the partitions in it (multi-cell partitions spread over their
              cells); every partition in a stretched column is padded so N/S abutment and face windows stay aligned
  tied      : lattice with every type padded uniformly over its instances (columns sharing a type tie together),
              plus the SIGNED (skip-list) types that the padding would touch
  python3 -I tools/die_plan/slot_lattice_cost.py PLAN.json GROWTH.json [--skip-types a,b] [--cell 1442.88,1226.88]
                                                 [--margin 103.68] [--out REPORT.json]
"""
import argparse
import collections
import json


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("growth")
    ap.add_argument("--skip-types", default="")
    ap.add_argument("--cell", default="1442.88,1226.88")
    ap.add_argument("--margin", type=float, default=103.68)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    P = json.load(open(a.plan))
    A = {r["type"]: r for r in json.load(open(a.growth))["types"]}
    skip = {s for s in a.skip_types.split(",") if s}
    T = P["partition_types"]
    PX, PY = (float(v) for v in a.cell.split(","))
    X0 = a.margin
    parts = []
    for p in P["partitions"]:
        w, h = T[p["type"]]["outline_um"]
        r = A.get(p["type"])
        gx, gy = (max(0.0, r["new_outline"][0] - w), max(0.0, r["new_outline"][1] - h)) if r else (0.0, 0.0)
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h, gx, gy = h, w, gy, gx
        if p["type"] in skip:
            gx = gy = 0.0
        x, y = p["origin_um"]
        parts.append(dict(name=p["name"], type=p["type"], x=x, y=y, w=w, h=h, g=(gx, gy),
                          cell=(int((x - X0 + 1) // PX), int((y - X0 + 1) // PY)),
                          n=(max(1, round(w / PX)), max(1, round(h / PY)))))

    def row_sum(ax):
        o = 1 - ax
        pos = "xy"[ax]
        size = "wh"[ax]
        opos, osize = "xy"[o], "wh"[o]
        idx = sorted(range(len(parts)), key=lambda i: parts[i][pos])
        sh = [0.0] * len(parts)
        for jj, j in enumerate(idx):
            pj = parts[j]
            s = 0.0
            for i in idx[:jj]:
                pi = parts[i]
                if min(pj[opos] + pj[osize], pi[opos] + pi[osize]) - max(pj[opos], pi[opos]) > 1e-3 and \
                        pi[pos] + pi[size] <= pj[pos] + 1e-3:
                    s = max(s, sh[i] + pi["g"][ax])
            sh[j] = s
        return round(max(sh[i] + parts[i]["g"][ax] for i in range(len(parts))), 1)

    def lattice(ax, tied):
        d = collections.defaultdict(float)
        for p in parts:
            for k in range(p["n"][ax]):
                d[p["cell"][ax] + k] = max(d[p["cell"][ax] + k], p["g"][ax] / p["n"][ax])
        occ = collections.defaultdict(set)
        for p in parts:
            occ[p["type"]].add((p["cell"][ax], p["n"][ax]))
        if tied:
            for _ in range(100):
                ch = False
                for t, ss in occ.items():
                    if len(ss) < 2:
                        continue
                    vals = [sum(d.get(c + k, 0.0) for k in range(n)) for c, n in ss]
                    m = max(vals)
                    for (c, n), v in zip(ss, vals):
                        if v < m - 1e-6:
                            d[c + n - 1] += m - v
                            ch = True
                if not ch:
                    break
        padded_signed = sorted({t for t, ss in occ.items() if t in skip and
                                any(sum(d.get(c + k, 0.0) for k in range(n)) > 1e-6 for c, n in ss)})
        return dict(total=round(sum(d.values()), 1), per_cell={k: round(v, 1) for k, v in sorted(d.items()) if v},
                    padded_signed=padded_signed)
    rep = {ax: dict(row_sum=row_sum(i), lattice=lattice(i, False), tied=lattice(i, True)) for i, ax in enumerate("xy")}
    if a.out:
        json.dump(rep, open(a.out, "w"), indent=1)
    for ax in "xy":
        r = rep[ax]
        print(f"{ax}: row_sum {r['row_sum']}  lattice {r['lattice']['total']}  tied {r['tied']['total']} "
              f"(padded signed {len(r['tied']['padded_signed'])})")


if __name__ == "__main__":
    main()
