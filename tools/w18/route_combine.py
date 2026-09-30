#!/usr/bin/env python3
"""W18: combine two layer-split die-route passes (tools/w18/die_route.py --only-classes / --exclude-classes)
into one congestion check: per 4x4-GCell block and layer, the usage of both passes against the RAW capacity
of the pass routed without a capacity adjustment on that layer.

    python3 tools/w18/route_combine.py --raw-cap A --also B --layers M8,M9 --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(work: Path) -> dict:
    g = {}
    for ln in (work / "gcell_usage.txt").read_text().splitlines():
        p = ln.split()
        if p[0] != "L":
            continue
        layer, j = p[1], int(p[2])
        for i, cu in enumerate(p[3:]):
            c, u = map(float, cu.split("/"))
            g[(layer, j, i)] = (c, u)
    return g


def emit(work: Path, layers: list, out: Path, min_frac: float) -> int:
    """One region adjustment per run of 4x4 blocks in a block row with the same used fraction (rounded up
    to 0.05): the next pass sees only the capacity this pass left."""
    lines = (work / "gcell_usage.txt").read_text().splitlines()
    gx = [int(v) for v in lines[0].split()[1].split(",")]
    gy = [int(v) for v in lines[1].split()[1].split(",")]
    dbu = 1000.0
    g = load(work)
    cmds = []
    for L in layers:
        rows = {}
        for (l, j, i), (c, u) in g.items():
            if l == L and c > 0 and u / c >= min_frac:
                rows.setdefault(j, []).append((i, min(1.0, -(-u / c // 0.05) * 0.05)))
        for j, lst in rows.items():
            lst.sort()
            run = None
            for i, f in lst + [(None, None)]:
                if run and i == run[1] + 1 and f == run[2]:
                    run[1] = i
                    continue
                if run:
                    x0 = gx[run[0] * 4] / dbu
                    x1 = gx[min(len(gx) - 1, run[1] * 4 + 4)] / dbu
                    y0, y1 = gy[j] / dbu, gy[min(len(gy) - 1, j + 4)] / dbu
                    cmds.append(f"set_global_routing_region_adjustment {{{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}}} "
                                f"-layer {L} -adjustment {round(run[2], 2)}")
                run = [i, i, f] if i is not None else None
    out.write_text("\n".join(cmds) + "\n")
    print(f"{len(cmds)} region adjustments -> {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw-cap", type=Path, required=True, help="pass whose capacity on --layers is unadjusted")
    ap.add_argument("--also", type=Path, required=True, help="the other pass (its usage is added)")
    ap.add_argument("--layers", default="M8,M9")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--emit-regions", type=Path, help="write region adjustments charging --raw-cap's usage on "
                    "--layers (for the next pass), instead of combining")
    ap.add_argument("--min-frac", type=float, default=0.05)
    a = ap.parse_args(argv)
    if a.emit_regions:
        return emit(a.raw_cap, a.layers.split(","), a.emit_regions, a.min_frac)
    A, B = load(a.raw_cap), load(a.also)
    out = {}
    for L in a.layers.split(","):
        keys = [k for k in A if k[0] == L]
        cap = sum(A[k][0] for k in keys)
        ua = sum(A[k][1] for k in keys)
        ub = sum(B.get(k, (0, 0))[1] for k in keys)
        over = [(k, A[k][1] + B.get(k, (0, 0))[1] - A[k][0]) for k in keys if A[k][1] + B.get(k, (0, 0))[1] > A[k][0]]
        peak = max(((A[k][1] + B.get(k, (0, 0))[1]) / A[k][0] if A[k][0] else 0.0) for k in keys)
        out[L] = dict(capacity=cap, usage_raw_cap_pass=ua, usage_other_pass=ub,
                      usage_pct=round(100 * (ua + ub) / cap, 2), blocks=len(keys),
                      overflow_blocks=len(over), overflow_tracks=sum(o for _, o in over),
                      peak_block_utilisation=round(peak, 3))
    rec = dict(schema="opentallas.v41.w18_route_combine.v1",
               basis="4x4-GCell blocks from each pass's gcell_usage.txt; usage summed, capacity from --raw-cap",
               layers=out,
               inputs={str(a.raw_cap): sha(a.raw_cap / "gcell_usage.txt"), str(a.also): sha(a.also / "gcell_usage.txt"),
                       "tool_sha256": sha(Path(__file__))})
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
