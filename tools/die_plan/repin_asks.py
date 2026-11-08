#!/usr/bin/env python3
"""TYPE-SAFE-2-AREA 11-08 (COORD 08:41 option C(2)): per-core face RE-PIN asks for the channel shortfall left after the
slot_channel_event repack/flip.  For every open channel (core face, need > new gap) the ask is the number of signal pins
to move off that face so the channel fits its new gap (pins x 0.048 / (layers x 0.7) <= gap), aggregated per core
MASTER (one re-pin serves every instance), with the face's pin-track use (OWNER (B): <= 70 % per face, M5/M6).

  python3 -I repin_asks.py EVENT PLAN --pins-root DIR --out ASKS.tsv [--layers 4]
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_channel_event as SC  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("event")
    ap.add_argument("plan")
    ap.add_argument("--pins-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--layers", type=float, default=4.0)
    ap.add_argument("--signed", default="", help="comma list of signed-off masters/types (a re-pin there = re-sign)")
    a = ap.parse_args()
    ev = json.loads(Path(a.event).read_text())
    P = json.loads(Path(a.plan).read_text())
    per = 0.048 / (a.layers * 0.7)
    agg = defaultdict(lambda: dict(types=set(), insts=0, move=0, short=0.0))
    meta = {}
    for r in ev["report"]:
        t = P["partition_types"][r["type"]]
        hcs = {h["inst"]: h for h in t.get("hard_cores", [])}
        for o in r.get("open", []):
            h = hcs.get(o["core"])
            if not h:
                continue
            o_ = h.get("orient", "R0")
            fc = SC.face_counts(h, a.pins_root)
            f = o["face"]
            # the face in the CORE frame (what the core owner re-pins)
            cf = f
            if o_ in ("MX", "R180") and f in "NS":
                cf = SC.OPP[f]
            if o_ in ("MY", "R180") and f in "EW":
                cf = SC.OPP[f]
            key = (h.get("module"), h.get("pins_file"), cf)
            mv = math.ceil(o["short"] / per - 1e-9)
            g = agg[key]
            g["types"].add(r["type"])
            g["insts"] += 1
            g["move"] = max(g["move"], min(mv, fc[f]))
            g["short"] = max(g["short"], o["short"])
            w, hh = h["outline_um"]
            edge = hh if cf in "EW" else w
            meta[key] = (fc[f], edge)
    signed = {x for x in a.signed.split(",") if x}
    rows = []
    for (mod, pf, cf), g in agg.items():
        pins, edge = meta[(mod, pf, cf)]
        tracks = edge / 0.064 * 2          # M5/M6 tracks along the face (two layers, 0.064 pitch)
        use = pins / tracks if tracks else 0.0
        use1 = (pins - g["move"]) / tracks if tracks else 0.0
        rows.append((g["short"], mod, pf, cf, pins, g["move"], round(g["short"], 2), round(use, 3), round(use1, 3),
                     g["insts"], "yes" if mod in signed else "no", ",".join(sorted(g["types"]))))
    rows.sort(key=lambda r: -r[0])
    with open(a.out, "w") as fo:
        fo.write("master\tpins_file\tcore_face\tface_pins\tmove_pins\tmax_short_um\tface_track_use\tafter_use\t"
                 "open_instances\tmaster_signed\ttypes\n")
        for r in rows:
            fo.write("\t".join(map(str, r[1:])) + "\n")
    print(json.dumps(dict(masters=len({r[1] for r in rows}), asks=len(rows), move_pins=sum(r[5] for r in rows),
                          over70=sum(1 for r in rows if r[7] > 0.70),
                          unsigned_asks=sum(1 for r in rows if r[10] == "no"),
                          unsigned_move_pins=sum(r[5] for r in rows if r[10] == "no"))))


if __name__ == "__main__":
    main()
