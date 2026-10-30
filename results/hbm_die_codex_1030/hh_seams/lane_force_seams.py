#!/usr/bin/env python3
"""Die-local ordered, exact-count station routing; no shared-tool or RTL change.

Each reachability layer is restricted to its specified partition. Wires may fly
over macros; every FF home stays on free lattice points outside macro halos.
Counts are tried unchanged first. Optional extra rounds add one stage per slot
and report every addition. Failed searches are candidate failures, not a proof
that no other floorplan/count vector can work.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


def ordered_route(masks, owners, start, end, xs, ys, reach, dilate, grid, stage_masks=None):
    xx, yy = xs[:, None], ys[None, :]
    da = np.abs(xx - start[0]) + np.abs(yy - start[1])
    db = np.abs(xx - end[0]) + np.abs(yy - end[1])
    stage_masks = stage_masks if stage_masks is not None else [masks[o] for o in owners]
    layers = [stage_masks[0] & (da <= reach + 1e-6)]
    if not layers[0].any():
        return None, 0
    radius = int(math.floor((reach + 1e-6) / grid))
    for stage, owner in enumerate(owners[1:], 1):
        layer = stage_masks[stage] & dilate(layers[-1], radius)
        if not layer.any():
            return None, stage
        layers.append(layer)
    good = layers[-1] & (db <= reach + 1e-6)
    if not good.any():
        return None, len(owners)
    q = tuple(int(i) for i in np.unravel_index(np.where(good, db, np.inf).argmin(), good.shape))
    rev = [q]
    for stage in range(len(owners) - 2, -1, -1):
        cx, cy = xs[q[0]], ys[q[1]]
        good = layers[stage] & (np.abs(xx - cx) + np.abs(yy - cy) <= reach + 1e-6)
        for used in rev:
            good[used] = False
        if not good.any():
            return None, stage
        fraction = (stage + 1) / (len(owners) + 1)
        tx = start[0] + (end[0] - start[0]) * fraction
        ty = start[1] + (end[1] - start[1]) * fraction
        score = np.abs(xx - tx) + np.abs(yy - ty)
        q = tuple(int(i) for i in np.unravel_index(np.where(good, score, np.inf).argmin(), good.shape))
        rev.append(q)
    pts = [(round(float(xs[i]), 4), round(float(ys[j]), 4)) for i, j in rev[::-1]]
    return pts, None


def install(LA, S, SR, chains, rounds, records):
    old_template = LA.Builder.template

    def template(self, src, dst):
        chain = chains.get(f"{src}>{dst}")
        if chain is None:
            return old_template(self, src, dst)
        assert chain[0] == src and chain[-1] == dst
        assert all(LA.shared_edge(self.P, a, b) for a, b in zip(chain, chain[1:]))
        return [("path", None, chain)]

    def resite(self, chain, slots, start, end):
        G, H, P = SR.G, SR.HALO, self.P
        rects = [P.rect(sl[0]) for sl in slots]
        # Global die lattice, not a grid shifted to a partition's bounding box.
        xs = np.arange(math.floor(min(r[0] for r in rects) / G),
                       math.ceil(max(r[2] for r in rects) / G) + 1) * G
        ys = np.arange(math.floor(min(r[1] for r in rects) / G),
                       math.ceil(max(r[3] for r in rects) / G) + 1) * G
        xx, yy = xs[:, None], ys[None, :]
        masks = []
        for sl, (x0, y0, x1, y1) in zip(slots, rects):
            m = ((xx > x0 + H) & (xx < x1 - H) & (yy > y0 + H) & (yy < y1 - H))
            for bx0, by0, bx1, by1 in S.placed_macro_boxes(P.ptype(sl[0]), halo=H).values():
                a, b = P.to_die(sl[0], (bx0, by0)), P.to_die(sl[0], (bx1, by1))
                ux0, ux1 = sorted((a[0], b[0])); uy0, uy1 = sorted((a[1], b[1]))
                m &= ~((xx > ux0 - 1e-6) & (xx < ux1 + 1e-6) &
                       (yy > uy0 - 1e-6) & (yy < uy1 + 1e-6))
            masks.append(m)
        original = [max(1, int(sl[8]), math.ceil(sl[10] / self.smax - 1e-9)) for sl in slots]
        pin_reach = 30.0  # Mandatory R2 boundary homes: first/last station near the actual abutting pin window.
        seams=[]
        for sl in slots:
            part,_,dfi,wi,_,dfo,wo,*_ = sl
            seams.append((self.face_pt(P,part,LA.OPP[dfi],wi),self.face_pt(P,part,dfo,wo)))
        base=[max(n,2,math.ceil(max(0,sl[10]-2*pin_reach)/self.reach-1e-9)+1) for n,sl in zip(original,slots)]
        for extra in range(rounds + 1):
            counts = [n + extra for n in base]
            owners = [i for i, n in enumerate(counts) for _ in range(n)]
            stage_masks=[]
            for i,n in enumerate(counts):
                first,last=seams[i]
                for j in range(n):
                    m=masks[i].copy()
                    if j==0:m &= (abs(xx-first[0])+abs(yy-first[1]) <= pin_reach+1e-6)
                    if j==n-1:m &= (abs(xx-last[0])+abs(yy-last[1]) <= pin_reach+1e-6)
                    stage_masks.append(m)
            pts, failed = ordered_route(masks, owners, start, end, xs, ys, self.reach, SR._dilate, G,stage_masks)
            record = dict(chain=chain, base_counts=original, seam_min_counts=base, counts=counts, pin_reach_um=pin_reach, seam_points=seams,
                          added_stations=sum(counts) - sum(original), reach_um=self.reach,
                          failed_stage=failed, status="FAIL" if pts is None else "PASS")
            records.append(record)
            print("ORDERED", json.dumps(record), flush=True)
            if pts is None:
                continue
            out, offset = [], 0
            for sl, n, mask in zip(slots, counts, masks):
                rr = pts[offset:offset + n]; offset += n
                assert len(rr) == n and sl[10] / n <= self.smax + 1e-6
                assert not self.macro_hits(sl[0], rr)
                out.append(rr)
            full = [start] + pts + [end]
            worst = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(full, full[1:]))
            assert worst <= self.reach + 1e-5
            via=[]
            for i,(rr,ends) in enumerate(zip(out,seams)):
                di=abs(rr[0][0]-ends[0][0])+abs(rr[0][1]-ends[0][1]);do=abs(rr[-1][0]-ends[1][0])+abs(rr[-1][1]-ends[1][1])
                assert di<=pin_reach+1e-5 and do<=pin_reach+1e-5
                if i:
                    a=out[i-1][-1];exit=seams[i-1][1];entry=ends[0];b=rr[0]
                    h=abs(a[0]-exit[0])+abs(a[1]-exit[1])+abs(exit[0]-entry[0])+abs(exit[1]-entry[1])+abs(b[0]-entry[0])+abs(b[1]-entry[1])
                    assert h<=self.reach+1e-5;via.append(h)
            record.update(max_hop_um=worst, max_via_seam_hop_um=max(via,default=0), regs_by_slot=out)
            return out
        return None

    LA.Builder.template, LA.Builder.resite = template, resite


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("wt", "plan", "rows", "out", "chains"):
        ap.add_argument(name)
    ap.add_argument("--first-id", type=int, default=700)
    ap.add_argument("--extra-rounds", type=int, default=3)
    ap.add_argument("--allow-cycle-event", action="store_true",
                    help="emit explicitly unadopted plan event even when new natural cycles differ")
    a = ap.parse_args()
    if Path(a.out).exists():
        ap.error("output must be a fresh directory; failed verdicts are immutable")
    sys.path.insert(0, str(Path(a.wt) / "tools/die_plan"))
    import lane_add as LA
    import schema as S
    import station_resite as SR
    records = []
    install(LA, S, SR, json.loads(Path(a.chains).read_text()), a.extra_rounds, records)
    if a.allow_cycle_event:
        old_init = LA.Builder.__init__
        def init(self, *args, **kwargs):
            old_init(self, *args, **kwargs)
            self.require_cycle_match = False
        LA.Builder.__init__ = init
    rep = LA.run(a.plan, a.rows, a.out, near_um=20000, first_id=a.first_id, max_hops=16)
    Path(a.out, "ordered_station_report.json").write_text(json.dumps(records, indent=1) + "\n")
    print(json.dumps(rep["totals"]), flush=True)
    for row in rep["built"] + rep["failed"]:
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
