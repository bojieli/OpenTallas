#!/usr/bin/env python3
"""DIE-HBM-75 11-05: reach-aware re-site of ft station-1 bit sites after ft_nudge.

ft_nudge.py re-sites only the bit cells that a plan delta put under a moved hard core, to the nearest free legal site
(<= 150 um), without looking at hop reach.  On HBM ev74 that pushed some station-1 bits of normal FT slots more than
405 um from their input-face S0 (check.py: 'real normal input S0->S1 > ft_station_max_um').  This tool changes only
those bits: for a bit with S0->S1 > LIMIT it picks the nearest free legal row site (same RowAllocator obstacles as
ft_nudge: placed macros + 1.08 um keep-off + clock-buffer halos; every other existing site reserved) to a target on
the S0 -> old-site line at TARGET um from S0, and accepts it only when S0->S1 <= LIMIT and S1->S2 <= STATION_MAX.
Station counts, windows, pins, outlines and cores never change.
    ft_reach_fix.py PLAN OUT LEDGER [TYPE:SLOT ...]   (default: every flagged normal slot)
"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import check as C  # noqa: E402
from die_hop_scan import pin_table, first_internal_hops, station_site, input_site, md  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402
from ft_nudge import KEEPOFF, CELL_DEFAULT, clock_points  # noqa: E402

LIMIT = 400.0          # S0->S1 accepted (5 um under the 405 rule for the cell-centre vs pin model)
STATION_MAX = 405.0
TARGETS = (390.0, 370.0, 350.0, 320.0, 290.0, 250.0)


def main():
    plan, out, ledger_f = sys.argv[1:4]
    only = {tuple(a.split(":", 1)) for a in sys.argv[4:]}
    raw = json.loads(Path(plan).read_text()); P = S.Plan(raw)
    ledger = []
    for tn, t in raw["partition_types"].items():
        slots = [s for s in t.get("ft_slots") or [] if s.get("bit_sites_um") and int(s.get("stations", 1)) >= 2
                 and (not only or (tn, s["name"]) in only)]
        if not slots:
            continue
        pins = pin_table(P, tn)
        bad = {}
        for s in slots:
            rows = [(b, d) for b, d in first_internal_hops(P, tn, s, pins=pins) if d > STATION_MAX + 1e-6]
            if rows:
                bad[s["name"]] = rows
        if not bad:
            continue
        w, h = t["outline_um"]
        macro = list(placement_boxes(t).values())
        boxes = [(a - KEEPOFF, b - KEEPOFF, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in macro]
        cpts = clock_points(t); hh = C.CLOCK_BUF_HALO_UM + 0.01
        cw0, ch0 = CELL_DEFAULT
        boxes += [(q[0] - hh - cw0, q[1] - hh - ch0, q[0] + hh, q[1] + hh) for q in cpts]
        alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL_DEFAULT,
                             column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
        for s in t["ft_slots"]:
            cw_, ch_ = s.get("bit_site_cell_um", CELL_DEFAULT)
            for st in s.get("bit_sites_um") or []:
                for x, y in st:
                    alloc.reserve_rectangle((x, y, x + cw_, y + ch_))
        for s in slots:
            if s["name"] not in bad:
                continue
            cw_, ch_ = s.get("bit_site_cell_um", CELL_DEFAULT)
            pi, po = pins[s["name"] + "_i"], pins[s["name"] + "_o"]
            k = int(s["stations"]); rec = dict(type=tn, slot=s["name"], bits=len(bad[s["name"]]), moved=0, worst_before=0.0,
                                               worst_after=0.0, max_move_um=0.0, failed=[])
            for bit, d0 in bad[s["name"]]:
                ap = pi[bit]; bp = po.get(bit) or ap
                a = np.array(input_site(ap)); old = np.array(station_site(s, 1, bit, ap, bp))
                nxt = np.array(station_site(s, 2, bit, ap, bp)) if k > 2 else np.array(input_site(bp))
                rec["worst_before"] = max(rec["worst_before"], round(d0, 1))
                done = False
                cands = [(a + (old - a) * (tgt / md(a, old)), 40.0) for tgt in TARGETS]
                cands += [(a + (nxt - a) * f, r) for r in (40.0, 80.0, 150.0) for f in (0.5, 0.42, 0.58, 0.34, 0.66)]
                for c, rad in cands:
                    try:
                        p, _ = alloc.allocate(c, 1, max_radius_um=rad)
                    except ValueError:
                        continue
                    q = p[0]
                    if md(a, q) <= LIMIT and md(q, nxt) <= STATION_MAX:
                        s["bit_sites_um"][0][bit] = [round(float(q[0] - cw_ / 2), 6), round(float(q[1] - ch_ / 2), 6)]
                        rec["moved"] += 1; rec["max_move_um"] = max(rec["max_move_um"], round(md(q, old), 2))
                        rec["worst_after"] = max(rec["worst_after"], round(md(a, q), 1))
                        done = True
                        break
                    # the allocator marked the site used; it stays reserved (a few spare sites, harmless)
                if not done:
                    rec["failed"].append(bit)
                    rec.setdefault("failed_why", []).append(dict(bit=bit, s0_s2=round(md(a, nxt), 1), s0_s1=round(d0, 1),
                                                                 s1_s2=round(md(old, nxt), 1)))
            ledger.append(rec)
    raw["note"] = "DIE-HBM-75 ft_reach_fix <- " + raw.get("note", "")[:200]
    Path(out).write_text(json.dumps(raw) + "\n")
    Path(ledger_f).write_text(json.dumps(ledger, indent=1) + "\n")
    print(f"slots {len(ledger)}; bits moved {sum(r['moved'] for r in ledger)}; failed {sum(len(r['failed']) for r in ledger)}; "
          f"worst after {max([r['worst_after'] for r in ledger] or [0])} um")
    return 1 if any(r["failed"] for r in ledger) else 0


if __name__ == "__main__":
    sys.exit(main())
