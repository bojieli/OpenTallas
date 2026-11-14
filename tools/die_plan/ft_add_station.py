#!/usr/bin/env python3
"""DIE-HBM-75 11-05 (COORD ruling: +1 station = +1 pin cycle): add one station to a normal FT slot with explicit bit sites.

The new station becomes S1: every bit gets a free legal row site (same obstacles as ft_nudge/ft_reach_fix: placed
macros + keep-off + clock-buffer halos, all existing sites reserved) near the middle of its input-face S0 and its old
S1, accepted only when both hops are <= 400 um.  The old S1..S(k-1) shift to S2..Sk unchanged; regs_um gets the new
centre.  The lane latency rows of every lane that crosses the slot get stations +1, cycles +1, natural +1.
    ft_add_station.py PLAN OUT LEDGER TYPE:SLOT[,TYPE:SLOT...] LANE[,LANE...]
"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import check as C  # noqa: E402
from die_hop_scan import pin_table, station_site, input_site, md  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402
from ft_nudge import KEEPOFF, CELL_DEFAULT, clock_points  # noqa: E402

LIMIT = 400.0


def main():
    plan, out, ledger_f, slots_a, lanes_a = sys.argv[1:6]
    raw = json.loads(Path(plan).read_text()); P = S.Plan(raw)
    ledger = []
    for ts in slots_a.split(","):
        tn, sn = ts.split(":")
        t = raw["partition_types"][tn]
        s = next(x for x in t["ft_slots"] if x["name"] == sn)
        k = int(s["stations"]); assert s.get("bit_sites_um") and len(s["bit_sites_um"]) == k - 1, (tn, sn)
        pins = pin_table(P, tn); pi, po = pins[sn + "_i"], pins[sn + "_o"]
        w, h = t["outline_um"]
        macro = list(placement_boxes(t).values())
        boxes = [(a - KEEPOFF, b - KEEPOFF, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in macro]
        cpts = clock_points(t); hh = C.CLOCK_BUF_HALO_UM + 0.01
        boxes += [(q[0] - hh - CELL_DEFAULT[0], q[1] - hh - CELL_DEFAULT[1], q[0] + hh, q[1] + hh) for q in cpts]
        alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL_DEFAULT,
                             column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
        for x in t["ft_slots"]:
            cw_, ch_ = x.get("bit_site_cell_um", CELL_DEFAULT)
            for st in x.get("bit_sites_um") or []:
                for bx, by in st:
                    alloc.reserve_rectangle((bx, by, bx + cw_, by + ch_))
        cw_, ch_ = s.get("bit_site_cell_um", CELL_DEFAULT)
        row, worst, failed = [], 0.0, []
        nb = len(s["bit_sites_um"][0])
        for bit in range(nb):
            ap = pi.get(bit) or po[bit]; bp = po.get(bit) or ap
            a = np.array(input_site(ap)); old = np.array(station_site(s, 1, bit, ap, bp))
            best = None
            for f, rad in ((0.5, 30.0), (0.5, 80.0), (0.4, 80.0), (0.6, 80.0), (0.5, 150.0), (0.3, 150.0), (0.7, 150.0)):
                try:
                    p, _ = alloc.allocate(a + (old - a) * f, 1, max_radius_um=rad)
                except ValueError:
                    continue
                q = p[0]
                if md(a, q) <= LIMIT and md(q, old) <= LIMIT:
                    best = q; break
            if best is None:
                # KV-FTGRID 11-14 (kv3_hgi_v3/v6 ft5 S3: 16 sites at half-pitch, place "explicit FT site is not on a row/site"):
                # the raw midpoint is off the row/site grid.  Take the nearest legal row site to it with no hop limit (the hop
                # is recorded as failed), and only if none exists within 150 um fail closed instead of emitting off-grid sites.
                failed.append(bit); mid = a + (old - a) * 0.5
                try:
                    best = alloc.allocate(mid, 1, max_radius_um=150.0)[0][0]
                except ValueError:
                    raise SystemExit(f"{tn}:{sn} bit {bit}: no legal row site within 150 um of the midpoint {mid.tolist()}")
            worst = max(worst, md(a, best), md(best, old))
            row.append([round(float(best[0] - cw_ / 2), 6), round(float(best[1] - ch_ / 2), 6)])
        s["bit_sites_um"].insert(0, row)
        c = np.mean(np.array(row) + [cw_ / 2, ch_ / 2], axis=0)
        regs = s.get("regs_um")
        if regs and len(regs) == k:
            regs.insert(1, [round(float(c[0]), 4), round(float(c[1]), 4)])
        s["stations"] = k + 1
        s["note"] = (s.get("note", "") + " | DIE-HBM-75 ev74f: +1 station (S1 new, COORD 11-05 +1 pin cycle)").strip(" |")
        ledger.append(dict(type=tn, slot=sn, stations=[k, k + 1], bits=nb, worst_hop_um=round(worst, 1), failed=failed))
    for ln in lanes_a.split(","):
        r = raw["latency"]["lanes"][ln]
        for f in ("stations", "cycles", "natural"):
            r[f] = int(r[f]) + 1
        ledger.append(dict(lane=ln, latency=r))
    raw["note"] = "DIE-HBM-75 ft_add_station <- " + raw.get("note", "")[:200]
    Path(out).write_text(json.dumps(raw) + "\n")
    Path(ledger_f).write_text(json.dumps(ledger, indent=1) + "\n")
    print(json.dumps([{k: v for k, v in r.items() if k != "failed"} | {"failed": len(r.get("failed", []))} for r in ledger]))
    return 1 if any(r.get("failed") for r in ledger) else 0


if __name__ == "__main__":
    sys.exit(main())
