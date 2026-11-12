#!/usr/bin/env python3
"""QC-VIS-RESITE: apply the VIS (s2_vis) hard-core positions/orients of the selected types onto a base plan.
Only origin_um / orient of each hard core change (inst set must match); stm types are snapped to the plan lattice
(grid_um, default 8.64) because their VIS origins sit on the 4.32 half-lattice; the 4.32 residual cannot go into
track_offset_um (schema: |track_offset| < BASE_LATTICE_UM 2.16), so the origin itself moves to the nearest legal
lattice point (no overlap with the other cores + halo, inside the outline).
    compose.py BASE VIS TYPES_JSON[,TYPES_JSON...] OUT [--snap-prefix sle_stm,slw_stm]
"""
import json, sys, itertools

GRID = 8.64


def box(hc, o=None):
    x, y = o or hc["origin_um"]; w, h = hc["outline_um"]; dx, dy = hc.get("track_offset_um", [0, 0])
    if hc.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    return (x + dx, y + dy, x + dx + w, y + dy + h)


def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0); dy = max(b[1] - a[3], a[1] - b[3], 0)
    return max(dx, dy) if (dx == 0 or dy == 0) else (dx * dx + dy * dy) ** .5


def snap_type(t, log):
    hcs = t["hard_cores"]; W, H = t["outline_um"]
    for i, hc in enumerate(hcs):
        ox, oy = hc["origin_um"]
        if abs(ox / GRID - round(ox / GRID)) < 1e-6 and abs(oy / GRID - round(oy / GRID)) < 1e-6:
            continue
        others = [box(o) for j, o in enumerate(hcs) if j != i]
        halo = max(hc.get("halo_um", 0), 4.32)
        cands = []
        for fx, fy in itertools.product((-1, 0, 1, 2), repeat=2):
            nx = round((int(ox // GRID) + fx) * GRID, 6); ny = round((int(oy // GRID) + fy) * GRID, 6)
            b = box(hc, (nx, ny))
            if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H:
                continue
            if any(gap(b, o) < 2 * halo - 1e-6 for o in others):
                continue
            cands.append((abs(nx - ox) + abs(ny - oy), nx, ny))
        if not cands:
            raise SystemExit(f"no legal lattice point for {hc['inst']} near {hc['origin_um']}")
        d, nx, ny = min(cands)
        log.append(dict(inst=hc["inst"], frm=[ox, oy], to=[nx, ny], move_um=round(d, 3)))
        hc["origin_um"] = [nx, ny]


def main():
    base, vis, tl, out = sys.argv[1:5]
    snap_pref = tuple(sys.argv[sys.argv.index("--snap-prefix") + 1].split(",")) if "--snap-prefix" in sys.argv else ("sle_stm", "slw_stm")
    P = json.load(open(base)); V = json.load(open(vis))
    types = [t for f in tl.split(",") for t in json.load(open(f))]
    rep = {}
    for tn in types:
        t = P["partition_types"][tn]; v = V["partition_types"][tn]
        assert [h["inst"] for h in t["hard_cores"]] == [h["inst"] for h in v["hard_cores"]], tn
        assert t["outline_um"] == v["outline_um"], tn
        moved = 0
        for a, b in zip(t["hard_cores"], v["hard_cores"]):
            assert a["module"] == b["module"] and a["outline_um"] == b["outline_um"]
            assert a.get("track_offset_um") == b.get("track_offset_um")
            if a["origin_um"] != b["origin_um"] or a.get("orient") != b.get("orient"):
                moved += 1
            a["origin_um"] = list(b["origin_um"]); a["orient"] = b.get("orient", "R0")
        log = []
        if tn.startswith(snap_pref):
            snap_type(t, log)
        rep[tn] = dict(moved=moved, snapped=log)
    ind = 1 if open(base).read(2) == "{\n" else None
    open(out, "w").write(json.dumps(P, indent=ind) + "\n")
    json.dump(rep, open(out + ".compose.json", "w"), indent=1)
    for tn, r in rep.items():
        print(tn, "moved", r["moved"], "snapped", len(r["snapped"]), "max_snap_um", max([s["move_um"] for s in r["snapped"]] or [0]))


if __name__ == "__main__":
    main()
