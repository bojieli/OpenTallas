#!/usr/bin/env python3
"""CLOCK-KV-R22 (KV-KITS-2 blocker): clip partition_types[*].clock.die_islands_um to the type outline.

The KV pc-family islands (kv3_pc_v1 43 / kv3_pc 8 / kv3_pc_v3 7 rects) start at x = -0.54: the 0.54-um west halo of a
die mesh driver placed on the partition's west edge (x = 0) was written in the type frame unclipped.  The part outside
the outline lies in the abutted neighbour and is that neighbour's reservation, so the island is CLIPPED to the outline
(the cell body is inside: the clip only removes halo), then snapped inward to the ASAP7 site/row lattice
(0.054 / 0.27).  Refuses if a clipped rect is empty or overlaps a hard core / keep-out.
usage: clip_islands.py PLAN.json OUT_PLAN.json OUT_ISLANDS.json"""
import hashlib
import json
import math
import sys
from pathlib import Path

SX, RY = 0.054, 0.27


def snap_in(v, g, up):
    q = v / g
    return round((math.ceil(q - 1e-6) if up else math.floor(q + 1e-6)) * g, 4)


def clip(r, W, H):
    """clip only the coordinates outside the outline, each snapped inward to the lattice; others unchanged."""
    return [r[0] if r[0] >= 0 else 0.0, r[1] if r[1] >= 0 else 0.0,
            r[2] if r[2] <= W else snap_in(W, SX, False), r[3] if r[3] <= H else snap_in(H, RY, False)]


def outside(r, W, H):
    return r[0] < -1e-9 or r[1] < -1e-9 or r[2] > W + 1e-9 or r[3] > H + 1e-9


def main(argv=None):
    plan, out_plan, out_isl = (argv or sys.argv[1:])
    raw_b = Path(plan).read_bytes()
    P = json.loads(raw_b)
    rep, fixed = {}, {}
    for tn, t in P["partition_types"].items():
        ck = t.get("clock") or {}
        rs = ck.get("die_islands_um") or []
        W, H = t["outline_um"]
        bad = [r for r in rs if outside(r, W, H)]
        if not bad:
            continue
        new = [clip(r, W, H) for r in rs]
        ko = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
               h["origin_um"][1] + h["outline_um"][1]) for h in t.get("hard_cores", []) or []]
        ko += [tuple(k) for k in ck.get("keepouts_um", [])]
        pre = []
        for o, n in zip(rs, new):
            if n[0] >= n[2] or n[1] >= n[3]:
                raise SystemExit(f"{tn}: island {o} empty after clipping")
            for k in ko:
                if n[0] < k[2] and k[0] < n[2] and n[1] < k[3] and k[1] < n[3]:
                    if o != n:
                        raise SystemExit(f"{tn}: clipped island {n} overlaps {k}")
                    pre.append([n, list(k)])    # pre-existing (unchanged rect): reported, not this fix's scope
        assert not any(outside(r, W, H) for r in new)
        ck["die_islands_um"] = new
        fixed[tn] = new
        rep[tn] = dict(islands=len(rs), outside_before=len(bad), outside_after=0,
                       changed=[[o, n] for o, n in zip(rs, new) if o != n][:5],
                       changed_n=sum(1 for o, n in zip(rs, new) if o != n),
                       preexisting_hard_core_overlaps=len(pre), preexisting_eg=pre[:5])
    s = json.dumps(P, indent=1)
    Path(out_plan).write_text(s)
    out = dict(lane="CLOCK-KV-R22", rule=__doc__, base_plan=plan, base_plan_sha256=hashlib.sha256(raw_b).hexdigest(),
               out_plan_sha256=hashlib.sha256(s.encode()).hexdigest(), types=rep, die_islands_um=fixed)
    Path(out_isl).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: {kk: v[kk] for kk in ("islands", "outside_before", "changed_n", "preexisting_hard_core_overlaps")} for k, v in rep.items()}),
          out["out_plan_sha256"][:8])


if __name__ == "__main__":
    sys.exit(main())
