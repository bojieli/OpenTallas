#!/usr/bin/env python3
"""DIE-HEAD-5 TILEIO (COORD 01:2x DRT-TRIAL-1 (5)): plan-declared local reset consumers for every soft HEAD type.

Root cause: the wavefront reset's final hop is tied to the CLOCK entry pins (reset_taps.tcl: one terminal per clk /
clk_t<i> BTerm).  The FB1 die-clock form (one region-root entry per partition) leaves ONE terminal per partition, so a
single launch flop must reach the whole partition (hd_tile 1023.8 um, hd_serdes 2583 um vs the 405-um relay reach); the
canonical grid taps also miss (hd_tile 511.9, hd_spn 654.8, hd_serdes 1325.2).  Fix (existing shared opt-in,
reset_tree.consumer_taps / type.reset.local_taps_um): local reset terminal relays at plan sites chosen so EVERY free
(non-core, non-keepout) point of the type is within --cover-um (default 300, margin under 405 for placement) of a LOCAL
site alone, i.e. independent of the clock form.  Greedy set cover on an 8.64-um candidate grid, then redundant-site prune.

    head_reset_local_taps.py PLAN.json [PLAN2.json ...] --tools tools/die_plan [--cover-um 300] [--write]
"""
import argparse
import json
import sys
from pathlib import Path


def cover_sites(w, h, blk, clear, R, g=17.28, tg=17.28, fine=4.32, site_excl=()):
    import numpy as np
    def grid(step):
        xs = np.arange(1, int(w / step)) * step
        ys = np.arange(1, int(h / step)) * step
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        return X.ravel(), Y.ravel()
    def keep(X, Y, m, inclusive):
        ok = (X >= clear) & (X <= w - clear) & (Y >= clear) & (Y <= h - clear)
        for a, b, c, d in blk:
            if inclusive:
                ok &= ~((X >= a - m) & (X <= c + m) & (Y >= b - m) & (Y <= d + m))
            else:
                ok &= ~((X > a - m) & (X < c + m) & (Y > b - m) & (Y < d + m))
        return ok
    TX, TY = grid(tg); k = keep(TX, TY, 0.0, True); TX, TY = TX[k], TY[k]
    if w * h < 1.0e6:                            # small types (hd_tile, hd_turn_*): narrow core streets need a fine site grid
        g = 4.32
    CX, CY = grid(g); k = keep(CX, CY, 2.0, False)
    for a, b, c, d in site_excl:                 # isolated-PG domain (VDDPHY): no core-domain relay sites inside
        k &= ~((CX >= a - 8.64) & (CX <= c + 8.64) & (CY >= b - 8.64) & (CY <= d + 8.64))
    CX, CY = np.round(CX[k], 3), np.round(CY[k], 3)
    FX, FY = grid(fine); k = keep(FX, FY, 0.0, True); FX, FY = FX[k], FY[k]
    tol = R + 12.0
    for _ in range(8):                           # cutting planes: add fine points the coarse cover misses
        un = np.ones(TX.size, bool); S = []
        D = lambda cx, cy: np.abs(TX - cx) + np.abs(TY - cy)
        while un.any():
            ux, uy = TX[un], TY[un]
            cnt = np.zeros(CX.size, int)
            for i in range(0, CX.size, 256):    # chunked |C| x |U| count
                cnt[i:i + 256] = ((np.abs(CX[i:i + 256, None] - ux[None]) + np.abs(CY[i:i + 256, None] - uy[None])) <= R).sum(1)
            b = int(cnt.argmax())
            if cnt[b] == 0:
                raise SystemExit(f"uncoverable points, e.g. {list(zip(ux[:3], uy[:3]))}")
            S.append((float(CX[b]), float(CY[b])))
            un &= D(*S[-1]) > R
        for s in list(S):                       # prune sites whose targets the others cover
            rest = [x for x in S if x != s]
            if rest and (np.min([D(*x) for x in rest], 0) <= R).all():
                S = rest
        fd = np.min([np.abs(FX - x) + np.abs(FY - y) for x, y in S], 0)   # checked on the fine grid
        worst = float(fd.max())
        if worst <= tol:
            break
        miss = fd > R
        TX, TY = np.concatenate([TX, FX[miss]]), np.concatenate([TY, FY[miss]])
    return S, worst, int(FX.size)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plans", nargs="+")
    ap.add_argument("--tools", required=True)
    ap.add_argument("--cover-um", type=float, default=300.0)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--types", default="", help="comma list (default every used soft type)")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.tools)
    import reset_tree as RT
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fallback_land import phy_rect_type_frame
    rows = {}
    base = json.loads(Path(a.plans[0]).read_text())
    used = {p["type"] for p in base["partitions"]}
    for tn, t in sorted(base["partition_types"].items()):
        if t.get("hard") or tn not in used or (a.types and tn not in a.types.split(",")):
            continue
        w, h = t["outline_um"]
        phy = phy_rect_type_frame(base, tn)
        S, worst, n = cover_sites(w, h, RT.blockages(t), RT.CLEAR_UM, a.cover_um, site_excl=[phy] if phy else [])
        rows[tn] = dict(local_taps_um=[list(s) for s in S], worst_um=round(worst, 2), targets=n)
        print(f"{tn:12s} {w:8.2f}x{h:8.2f} local taps {len(S):2d} worst {worst:7.2f} um (fine 4.32 grid, {n} pts)", flush=True)
    if a.write:
        for f in a.plans:
            src = Path(f).read_text()
            p = json.loads(src)
            fmt = next((k for k in [(i, nl, sep) for i in (2, 1, None) for nl in ("\n", "") for sep in (None, (",", ":"))]
                        if json.dumps(p, indent=k[0], separators=k[2]) + k[1] == src), (2, "\n", None))
            for tn, r in rows.items():
                p["partition_types"][tn].setdefault("reset", {})["local_taps_um"] = r["local_taps_um"]
            Path(f).write_text(json.dumps(p, indent=fmt[0], separators=fmt[2]) + fmt[1])
            print(f"wrote {f} (format indent={fmt[0]})")
    return rows


if __name__ == "__main__":
    main()
