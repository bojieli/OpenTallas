#!/usr/bin/env python3
"""Static per-type cut check over ALL planned partition-level nets (PATH-HBM 2026-10-25): ft slots (ft_cut.slot_paths)
plus internal_stations core links (from_um -> regs_um -> to_um, Manhattan L legs, horizontal first).  At each cut line
(every `step` um; vertical lines for horizontal demand, horizontal lines for vertical demand) the demand counts each
NET once (internal links are keyed by their launch pin, so a fan-out bus that appears in several internal_stations
entries is not summed again -- the over-count of the 12:06 R1 measure, e.g. L12_o 8836 vs 3143 b), and each ft slot
once.  Capacity = free M4+M6 (H) or M5+M7 (V) tracks across the cut, 0 over hard cores whose top layer covers it
(ft_cut.cut_capacity with share 1.0 = the partition's own glue layers; die_ft_bands at their die_share).
Ratio rule <= 0.55-0.60 (OWNER 10-12).  Optional --window x0 x1 y0 y1 restricts cuts to a region (e.g. a corridor)."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402
import ft_cut as F  # noqa: E402


def legs(pts):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 != x1:
            out.append(((x0, y0), (x1, y0)))
        if y0 != y1:
            out.append(((x1, y0), (x1, y1)))
    return out


def nets(P, tn):
    t = P.types[tn]
    res = {}
    for name, wd, pts, _ in F.slot_paths(P, tn):
        res["ft:" + name] = (wd, [legs([tuple(p) for p in pts])])
    for s in t.get("internal_stations", []) or []:
        key = "net:" + (s.get("launch") or s["conn"])
        pts = [tuple(s["from_um"])] + [tuple(r) for r in s.get("regs_um", [])] + [tuple(s["to_um"])]
        wd, L = res.get(key, (0, []))
        res[key] = (max(wd, int(s.get("bits", 1))), L + [legs(pts)])
    return res


def scan(P, tn, step=8.64, win=None):
    t = P.types[tn]
    w, h = t["outline_um"]
    N = nets(P, tn)
    out = {}
    for horiz in (True, False):
        L = w if horiz else h
        prof, worst = [], (0.0, None, 0, 0, [])
        k = step / 2
        while k < L:
            dem, who = 0, []
            for key, (wd, polys) in N.items():
                hit = False
                for lg in polys:
                    for (x0, y0), (x1, y1) in lg:
                        if horiz and y0 == y1 and min(x0, x1) < k < max(x0, x1):
                            if win and not (win[2] <= y0 <= win[3]):
                                continue
                            hit = True
                        if not horiz and x0 == x1 and min(y0, y1) < k < max(y0, y1):
                            if win and not (win[0] <= x0 <= win[1]):
                                continue
                            hit = True
                        if hit:
                            break
                    if hit:
                        break
                if hit:
                    dem += wd
                    who.append((wd, key))
            if win and not ((win[0] <= k <= win[1]) if horiz else (win[2] <= k <= win[3])):
                k += step
                continue
            if dem:
                cap = F.cut_capacity(t, horiz, k, 1.0)
                if win:   # capacity only inside the window span
                    cap *= ((win[3] - win[2]) / h) if horiz else ((win[1] - win[0]) / w)
                r = dem / cap if cap else 99.0
                prof.append((round(k, 2), dem, round(cap), round(r, 3)))
                if r > worst[0]:
                    worst = (round(r, 3), round(k, 2), dem, round(cap), sorted(who, reverse=True)[:8])
            k += step
        out["cut_h" if horiz else "cut_v"] = dict(worst_ratio=worst[0], at=worst[1], demand_b=worst[2], cap_tracks=worst[3],
                                                   top=worst[4], profile=prof)
    out["nets"] = len(N)
    return out


def main():
    a = argparse.ArgumentParser()
    a.add_argument("plan"); a.add_argument("--type", required=True); a.add_argument("--step", type=float, default=8.64)
    a.add_argument("--window", nargs=4, type=float, metavar=("X0", "X1", "Y0", "Y1")); a.add_argument("--json")
    x = a.parse_args()
    P = S.Plan(S.load(x.plan))
    r = scan(P, x.type, x.step, x.window)
    for k in ("cut_h", "cut_v"):
        c = r[k]
        print(x.type, k, "worst", c["worst_ratio"], "at", c["at"], "demand", c["demand_b"], "cap", c["cap_tracks"], "top", c["top"][:4])
    if x.json:
        Path(x.json).write_text(json.dumps(r, indent=1) + "\n")


if __name__ == "__main__":
    main()
