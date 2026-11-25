#!/usr/bin/env python3
"""sink_bins_spread.py -- TAPBINS pass 2 (QC-CB-SPREAD-R2 11-24, COORD C1n): spread over-full sink bins to placeable density.

sink_bins_compose.py adds every plan row's flops at the row's site; a rank sited at one point (pad / landing / station ranks)
still lands hundreds to thousands of flops in one 10.8-um bin (slw_stm_v3: 1,856 in one bin, 8,825 in one 100-um window at the
die edge).  No placement holds that: a bin holds at most bin_um^2 x UTIL / FLOP_UM2 flops (sink_bins_compose constants, ~201 at
10.8 um).  The density tap solve then cannot get a tap under tap_target_sinks there (CB-TAPBINS pass 1: 33 types still planned
> 1,000 per tap).  Rule: every bin keeps max(cap, its native weight); the excess moves outward ring by ring (Manhattan rings
of bins) to the nearest bins with room that lie inside the outline and outside every placement obstacle (macro boxes), the way
the placer spreads it.  The total count is unchanged; deterministic (heavy bins first, ring cells in a fixed order).

  spread(bins, bin_um, outline, boxes, native=None, cap=None) -> (new_bins, report)
  sink_bins_spread.py PLAN --types a,b --bins-dir DIR [--report R.json]    (cwd = tree root; DIR relative)
     reads DIR/<type>__composed.json (+ its native_bins_file), writes DIR/<type>__spread.json (provenance: spread_from,
     cap, moved, max_bin before / after); the caller points clock.sink_bins_file at it.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FLOP_UM2 = 0.29
UTIL = 0.5


def bin_cap(bin_um):
    return int(bin_um * bin_um * UTIL / FLOP_UM2)


def _key(x, y, b):
    return (int(math.floor(x / b)), int(math.floor(y / b)))


def spread(bins, bin_um, outline, boxes=(), native=None, cap=None, max_ring=400):
    b = float(bin_um)
    cap = int(cap or bin_cap(b))
    w, h = map(float, outline)
    nx, ny = max(1, int(math.ceil(w / b))), max(1, int(math.ceil(h / b)))

    def ok(i, j):
        if not (0 <= i < nx and 0 <= j < ny):
            return False
        cx, cy = (i + 0.5) * b, (j + 0.5) * b
        return not any(a < cx < c and bb < cy < d for a, bb, c, d in boxes)

    load, nat = {}, {}
    for x, y, c in bins:
        k = _key(x, y, b)
        load[k] = load.get(k, 0.0) + float(c)
    for x, y, c in native or []:
        k = _key(x, y, b)
        nat[k] = nat.get(k, 0.0) + float(c)
    room = lambda k: max(cap, nat.get(k, 0.0)) - load.get(k, 0.0)  # noqa: E731
    before = max(load.values()) if load else 0.0
    moved, stuck = 0.0, 0.0
    for k in sorted([k for k in load if room(k) < 0], key=lambda k: (load[k], k), reverse=True):
        ex = -room(k)
        if ex <= 0:
            continue
        load[k] -= ex
        i0, j0 = k
        r = 0
        while ex > 1e-9 and r < max_ring:
            r += 1
            ring = []
            for di in range(-r, r + 1):
                dj = r - abs(di)
                ring.append((i0 + di, j0 + dj))
                if dj:
                    ring.append((i0 + di, j0 - dj))
            for c in ring:
                if ex <= 1e-9:
                    break
                if not ok(*c):
                    continue
                rm = room(c)
                if rm > 0:
                    t = min(rm, ex)
                    load[c] = load.get(c, 0.0) + t
                    ex -= t
                    moved += t
        if ex > 1e-9:                         # nowhere to go within max_ring: keep it (reported)
            load[k] += ex
            stuck += ex
    out = [[round((i + 0.5) * b, 3), round((j + 0.5) * b, 3), round(v, 3)] for (i, j), v in sorted(load.items()) if v > 1e-9]
    rep = dict(cap=cap, moved=round(moved), stuck=round(stuck), max_bin_before=round(before),
               max_bin_after=round(max(load.values()) if load else 0.0), n=round(sum(load.values())))
    return out, rep


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--types", required=True)
    ap.add_argument("--bins-dir", required=True)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    import schema  # noqa: F401  (placement_obstacles needs it on the path)
    from placement_obstacles import placement_boxes
    raw = json.loads(Path(a.plan).read_text())
    reps = {}
    for tn in [t for t in a.types.split(",") if t]:
        t = raw["partition_types"][tn]
        src = Path(a.bins_dir) / f"{tn}__composed.json"
        doc = json.loads(src.read_text())
        nat = json.loads(Path(doc["native_bins_file"]).read_text())["bins"] if doc.get("native_bins_file") else None
        boxes = list(placement_boxes(t).values())
        nb, rep = spread(doc["bins"], doc.get("bin_um", 10.8), t["outline_um"], boxes, nat)
        new = dict(doc, bins=nb, n=rep["n"], spread_from=str(src), spread_from_sha256=_sha(src), spread=rep,
                   source=doc.get("source", "") + " + sink_bins_spread.py (TAPBINS pass 2)")
        (Path(a.bins_dir) / f"{tn}__spread.json").write_text(json.dumps(new) + "\n")
        reps[tn] = rep
        print(tn, rep, flush=True)
    if a.report:
        Path(a.report).write_text(json.dumps(reps, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
