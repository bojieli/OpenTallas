#!/usr/bin/env python3
"""DIE-HBM-82-SPB d44v plan event: q_spb2 N->N turnaround ft slots L1278x3 / L1280x6 re-sited as nested U corridors
BELOW the xcal hard-core row, with explicit per-bit station sites.

Why (q_spb2 vA, 9 h of GRT without convergence): both turnarounds kept every internal station on the N edge
(regs_um y 1494.72, spiral clumps 12 um tall), so 1484 + 747 bits ran E-W through the 34-um strip between the
u_xc_Q2 core top (y 1468.8, OBS M1-M5) and the N edge; congestion-25.rpt: 100% of the capped 20000 gcells sit at
x 430-953 / y 1279-1502, srcs = L1278x3 / L1280x6 stations + L49_i internal stations.

Form: each bit runs its own Manhattan U: in pin -> down at its in-window x -> its band row y_b -> across -> up at its
out-window x -> out pin.  Bands sit below the xcal row (cores y >= 1244.16): L1278x3 (inner U) y [BAND_1278],
L1280x6 (outer U) y [BAND_1280], each sized for <= 0.5 of the M4+M6 tracks (27.3 tr/um after the 0.25 derate).
Inner lanes (the bit nearest the U interior on the in leg) take the top band row.  Station j (1..k-1) of every bit
sits at fraction j/k of that bit's own path length (equal per-bit hops, as ft_corridor bit paths), on the nearest
free row-legal site (RowAllocator, 2.16 x 0.27 grid at origin 4.32, cores + 2-um keep-off walls, every other slot's
explicit bit sites reserved).  Station counts, windows, pins, cores, outlines: unchanged (0 PIN CYCLES).

    mk_uturn.py POR_PLAN.json OUT_PLAN.json LEDGER.json
"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path.cwd()
sys.path.insert(0, str(HERE / "tools/die_plan")); sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
from gen_phys import type_pins  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402

TYPE = "q_spb2"
CELL = (1.404, .27)
KEEPOFF = 2.0
BANDS = {"L1278x3": (1065.0, 1175.0), "L1280x6": (995.0, 1055.0)}
TPU = 0.75 * (1 / .048 + 1 / .064)      # M4+M6 usable tracks / um (TYPE-SAFE-1 track_est deck)
BUDGET = 405.0 * 0.98 - 2.0              # ft_corridor hop budget


def main(plan_in, plan_out, ledger_out):
    raw = json.loads(Path(plan_in).read_text())
    model = S.Plan(raw)
    ty = model.types[TYPE]
    w, h = ty["outline_um"]
    pins = {(bn, i): (x, y) for bn, i, _, x, y, _ in type_pins(model, TYPE)}
    boxes = list(S.placed_macro_boxes(ty, halo=KEEPOFF).values())
    alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL,
                         column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
    slots = {s["name"]: s for s in ty["ft_slots"]}
    # reserve every other slot's explicit bit sites
    nres = 0
    for s in ty["ft_slots"]:
        if s["name"] in BANDS or not s.get("bit_sites_um"):
            continue
        cw, ch = s["bit_site_cell_um"]
        for st in s["bit_sites_um"]:
            for x, y in st:
                alloc.reserve_rectangle((x, y, x + cw, y + ch)); nres += 1
    ledger = dict(type=TYPE, reserved_other_sites=nres, budget_um=round(BUDGET, 2), slots=[])
    for name, (lo, hi) in BANDS.items():
        s = slots[name]
        assert s["in_face"] == "N" and s["out_face"] == "N" and s.get("turnaround"), name
        k = int(s["stations"]); nb = int(s["width"]) + 1
        a = np.array([pins[(name + "_i", i)] for i in range(nb)], float)
        b = np.array([pins[(name + "_o", i)] for i in range(nb)], float)
        west = b[:, 0].mean() < a[:, 0].mean()            # bundle turns west at the bottom
        u = (a[:, 0] - a[:, 0].min()) / max(np.ptp(a[:, 0]), 1e-9)
        inner = u if west else 1.0 - u                   # 0 = lane nearest the U interior
        yb = hi - inner * (hi - lo)
        P = np.stack([a, np.column_stack((a[:, 0], yb)), np.column_stack((b[:, 0], yb)), b], axis=1)
        Pseg = np.abs(np.diff(P, axis=1)).sum(axis=2)
        Pcum = np.concatenate([np.zeros((nb, 1)), np.cumsum(Pseg, axis=1)], axis=1)
        Lb = Pcum[:, -1]
        sites, reps = [], []
        for j in range(1, k):
            t = Lb * j / k
            seg = np.clip((t[:, None] >= Pcum[:, 1:3]).sum(axis=1), 0, 2)
            r = np.arange(nb)
            f = (t - Pcum[r, seg]) / np.maximum(Pseg[r, seg], 1e-9)
            q = P[r, seg] + (P[r, seg + 1] - P[r, seg]) * f[:, None]
            # allocate in lane order along the station's spread direction
            order = np.lexsort((q[:, 1], q[:, 0]))
            out = np.zeros((nb, 2))
            for bi in order:
                p, _ = alloc.allocate(q[bi], 1, max_radius_um=40.0)
                out[bi] = p[0]
            sites.append(out)
            c = out.mean(axis=0)
            reps.append(out[np.argmin(np.abs(out - c).sum(axis=1))])
        chain = [a, *sites, b]
        hops = [float(np.abs(q - p).sum(axis=1).max()) for p, q in zip(chain, chain[1:])]
        disp = []
        for j, st in enumerate(sites, 1):
            t = Lb * j / k
            disp.append(None)
        if max(hops) > BUDGET + 1e-6:
            raise SystemExit(f"{name}: hop {max(hops):.1f} > budget {BUDGET:.1f}")
        for st in sites:
            for x, y in st:
                for (bx0, by0, bx1, by1) in boxes:
                    if bx0 < x < bx1 and by0 < y < by1:
                        raise SystemExit(f"{name}: site {x},{y} inside a core box")
        old = dict(regs_um=s["regs_um"], had_bit_sites=bool(s.get("bit_sites_um")))
        s["regs_um"] = [a.mean(axis=0).round(4).tolist()] + [rp.round(4).tolist() for rp in reps]
        s["bit_site_cell_um"] = list(CELL)
        s["bit_sites_um"] = [(p - np.array([CELL[0] / 2, CELL[1] / 2])).round(6).tolist() for p in sites]
        ext = [[round(float(st[:, 0].min()), 2), round(float(st[:, 0].max()), 2), round(float(st[:, 1].min()), 2),
                round(float(st[:, 1].max()), 2)] for st in sites]
        ledger["slots"].append(dict(slot=name, bits=nb - 1, stations=k, turn="west" if west else "east",
                                    band_um=[lo, hi], band_track_use=round((nb - 1) / ((hi - lo) * TPU), 3),
                                    len_um=[round(float(Lb.min()), 1), round(float(Lb.max()), 1)],
                                    hops_um=[round(x, 1) for x in hops], station_extent_um=ext,
                                    regs_um_old=old["regs_um"], regs_um_new=s["regs_um"]))
        print(f"{TYPE}/{name}: {nb-1} b, k={k}, band {lo}-{hi} U={ledger['slots'][-1]['band_track_use']}, "
              f"len {Lb.min():.0f}-{Lb.max():.0f}, hops {[round(x) for x in hops]}, extents {ext}")
    Path(plan_out).write_text(json.dumps(raw) + "\n")
    Path(ledger_out).write_text(json.dumps(ledger, indent=1) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])
