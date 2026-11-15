#!/usr/bin/env python3
"""S81-LEAF-T14 11-15 (COORD r88, FABLE-CLOSURE-STRATEGY lever 4): internal_stations register sites inside a hard-core box.

For every type, every internal_stations row whose regs_um point lies strictly inside a placed macro / probe box gets that
register moved to the free point (outside every box + GAP) that keeps the row's worst hop (from_um -> regs -> to_um,
Manhattan) <= max(LIMIT, the row's hop before), nearest to the old site first (ring search, 2.16 um steps, <= RMAX).
Register counts, cycles, bits, pins, cores unchanged.  Rows with no such point are REFUSED and listed.

  istation_clear.py PLAN OUT_ROWS LEDGER [--type RE] [--gap 2.0] [--rmax 150]
"""
import argparse, json, math, os, re, sys
from pathlib import Path
TD = os.environ.get("TD") or str(Path(__file__).resolve().parent)
sys.path[:0] = [TD, os.path.dirname(os.path.dirname(TD))]
import schema as S, ft_seam_fix as SF

LIMIT = 400.0
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
def hops(e, regs=None):
    pts = [e["from_um"]] + list(regs if regs is not None else e["regs_um"]) + [e["to_um"]]
    return [md(a, b) for a, b in zip(pts, pts[1:])]
def inside(boxes, p, gap=0.0):
    return any(b[0] - gap < p[0] < b[2] + gap and b[1] - gap < p[1] < b[3] + gap for b in boxes)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("ledger")
    ap.add_argument("--type", default="."); ap.add_argument("--gap", type=float, default=2.0); ap.add_argument("--rmax", type=float, default=150.0)
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text()); rows = {}; led = []
    for tn, t in sorted(raw["partition_types"].items()):
        if not re.search(a.type, tn): continue
        ist = t.get("internal_stations") or []
        if not ist: continue
        try: boxes = SF.macro_boxes(t)
        except Exception: continue
        W, H = t["outline_um"]
        rec = dict(type=tn, rows=0, regs=0, bits=0, refused=[]); changed = False
        for i, e in enumerate(ist):
            regs = e.get("regs_um") or []
            if not regs or not e.get("from_um") or not e.get("to_um"): continue
            bad = [k for k, p in enumerate(regs) if inside(boxes, p)]
            if not bad: continue
            lim = max(LIMIT, max(hops(e))); new = [list(p) for p in regs]; fail = False
            for k in bad:
                best = None; r = 0.0
                step = 2.16
                n = int(a.rmax / step)
                cands = sorted(((dx * step, dy * step) for dx in range(-n, n + 1) for dy in range(-n, n + 1)),
                               key=lambda q: abs(q[0]) + abs(q[1]))
                for dx, dy in cands:
                    p = [regs[k][0] + dx, regs[k][1] + dy]
                    if not (4.32 < p[0] < W - 4.32 and 4.32 < p[1] < H - 4.32) or inside(boxes, p, a.gap): continue
                    trial = new[:k] + [p] + new[k + 1:]
                    if max(hops(e, trial)) <= lim + 1e-6:
                        best = [round(p[0], 3), round(p[1], 3)]; break
                if best is None: fail = True; break
                new[k] = best
            if fail:
                rec["refused"].append(dict(row=i, conn=e.get("conn"), bits=e.get("bits", 1), regs_inside=len(bad))); continue
            e["regs_um"] = new
            e["note"] = (e.get("note", "") + " | istation_clear 11-15: %d reg site(s) out of cores" % len(bad)).strip(" |")
            rec["rows"] += 1; rec["regs"] += len(bad); rec["bits"] += int(e.get("bits", 1)) * len(bad); changed = True
        if rec["rows"] or rec["refused"]:
            led.append(rec)
        if changed: rows[tn] = t
    Path(a.out).write_text(json.dumps(rows) + "\n"); Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
    print("types changed %d, rows %d, regs %d, bits %d, refused rows %d (types %d)" % (len(rows), sum(r["rows"] for r in led),
          sum(r["regs"] for r in led), sum(r["bits"] for r in led), sum(len(r["refused"]) for r in led), sum(1 for r in led if r["refused"])))
    return 0
if __name__ == "__main__":
    sys.exit(main())
