#!/usr/bin/env python3
"""pose_spread.py -- conservative density relief for a reviewed native FF pose (S81-T51-RECUT, OWNER 11-06 21:5x).

The exact native pose inherits dense FF clumps (t51 u_cland_ft*: bins 0.9 local density, GRT M2/M3 usage ~1.0).  This
spreads every posed FF of each selected module about the module's own area centroid by --scale, shifting the centroid
inward so the scaled box stays in the die, then snaps to the site/row grid (orientation from the row, as in the input
pose) and legalizes with station_face_copies.legalize.  Same FF names and masters, same netlist: 0 added cycles.

    pose_spread.py IN.tcl OUT.tcl --modules REGEX --scale 2 --die W H --blockages FILE [--max-move UM] [--json OUT.json]
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from station_face_copies import SITE_W, legalize, read_blockages, read_pose  # noqa: E402

ROW_H = 0.27


FAMILY = ({"R0", "MY"}, {"R180", "MX"})    # legal orientations of one row parity (x-flip free)
ROW_FLIP = {"R0": "MX", "MX": "R0", "MY": "R180", "R180": "MY"}     # same x-flip on a row of the other parity


def row_orients(sites):
    """row index parity -> orientation family, from the input pose; a parity holding both families is refused"""
    seen = collections.defaultdict(set)
    for x, y, w, h, o, m in sites.values():
        seen[round(y / ROW_H) % 2].add(o)
    out = {}
    for k, v in seen.items():
        fam = [f for f in FAMILY if v <= f]
        if not fam:
            raise ValueError(f"pose orientation is not one family per row parity: {dict(seen)}")
        out[k] = fam[0]
    return out


def spread(sites, regex, scale, die, rows, max_move=60.0):
    """returns (new sites, per-module stats); rows = sorted legal row y values; each FF moves at most max_move um in x
    and in y, so a far outlier of a module is not stretched into a longer wire (the dense core is what needs relief)"""
    W, H = die
    row_orients(sites)
    rx = re.compile(regex)
    groups = collections.defaultdict(list)
    for n in sites:
        m = rx.search(n)
        if m:
            groups[m.group(0)].append(n)
    out = dict(sites)
    stats = {}
    lo_row, hi_row = rows[0], rows[-1]
    for mod, names in sorted(groups.items()):
        A = sum(sites[n][2] * sites[n][3] for n in names)
        cx = sum(sites[n][0] * sites[n][2] * sites[n][3] for n in names) / A
        cy = sum(sites[n][1] * sites[n][2] * sites[n][3] for n in names) / A
        dx0 = (cx - min(sites[n][0] for n in names)) * scale
        dx1 = (max(sites[n][0] + sites[n][2] for n in names) - cx) * scale
        dy0 = (cy - min(sites[n][1] for n in names)) * scale
        dy1 = (max(sites[n][1] + sites[n][3] for n in names) - cy) * scale
        # shift inward so the scaled box fits; a box larger than the die is centred and then clamped
        ncx = max(dx0, cx) if dx0 + dx1 >= W else min(max(cx, dx0), W - dx1)
        ncy = max(dy0, cy) if dy0 + dy1 >= H else min(max(cy, dy0), H - dy1)
        moved = 0.0
        for n in names:
            x, y, w, h, o, ma = sites[n]
            tx = x + max(-max_move, min(max_move, ncx + (x - cx) * scale - x))
            ty = y + max(-max_move, min(max_move, ncy + (y - cy) * scale - y))
            nx = round(round(min(W - w, max(0.0, tx)) / SITE_W) * SITE_W, 6)
            ny = min(hi_row, max(lo_row, round(round(ty / ROW_H) * ROW_H, 6)))
            same = round(ny / ROW_H) % 2 == round(y / ROW_H) % 2
            out[n] = (nx, ny, w, h, o if same else ROW_FLIP[o], ma)
            moved = max(moved, abs(nx - x) + abs(ny - y))
        stats[mod] = {"ffs": len(names), "centroid": [round(cx, 2), round(cy, 2)], "new_centroid": [round(ncx, 2), round(ncy, 2)],
                      "max_move_um": round(moved, 1)}
    return out, stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pose"); ap.add_argument("out")
    ap.add_argument("--modules", required=True); ap.add_argument("--scale", type=float, required=True)
    ap.add_argument("--die", nargs=2, type=float, required=True); ap.add_argument("--blockages", required=True)
    ap.add_argument("--max-move", type=float, default=60.0); ap.add_argument("--json")
    a = ap.parse_args(argv)
    text, sites = read_pose(a.pose)
    blk = read_blockages(a.blockages)
    rows = sorted({round(b[2], 4) for b in blk})
    new, stats = spread(sites, a.modules, a.scale, a.die, rows, a.max_move)
    if not stats:
        raise SystemExit(f"no posed FF matches {a.modules!r}")
    moves = legalize(new, blk)

    def sub(m):
        x, y, w, h, o, ma = new[m.group(1)]
        return f" {{{m.group(1)}}} {{{x:.6f} {y:.6f} {w:.6f} {h:.6f} {o} {ma}}} \\"
    res = re.sub(r"^ \{(.+?)\} \{[0-9.]+ [0-9.]+ [0-9.]+ [0-9.]+ \S+ \S+\} \\$", sub, text, flags=re.M)
    Path(a.out).write_text(res)
    rep = {"modules": stats, "legalize_moves": len(moves), "ffs_total": len(new), "scale": a.scale, "max_move_um": a.max_move}
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"POSE_SPREAD {len(stats)} modules {sum(s['ffs'] for s in stats.values())} of {len(new)} FFs scale {a.scale} legalize_moves {len(moves)}")


if __name__ == "__main__":
    main()
