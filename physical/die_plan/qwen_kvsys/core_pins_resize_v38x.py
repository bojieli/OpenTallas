#!/usr/bin/env python3
"""KVG3-CORES 10-24: plan v3.8x pins files for the head_eighth slot shrink 285.12 -> 216 um (KV-G3 ruling on the
KVG3-CORES review-before-route: head_eighth fill 22-33%, ectl channel 25.92 um).

Re-spreads an existing top-down pins file (core_pins_v37p.py, KV-P6-PINS) onto a new outline with the SAME pin -> face
assignment and pin order (the face choice depends on partner directions, which a shrink about the same origin does not
change) and the SAME spreading rule as core_pins_v37p.py: per face, evenly over the face length minus the 2.16 um
corner keep-out, on the symmetric plan tracks (N/S M5 x-tracks, E/W M4 y-tracks, offset pitch/2, so every orient stays
on track); a face over 1 pin / 2 tracks spills onto M7 / M6 in proportion to the track counts.
core_pins_v37p.py itself is not re-run: it re-derives every planned core of the plan (and re-applies its v3.7 layout
moves), which would rewrite pins files and core_conns.json of cores this step does not change.

    core_pins_resize_v38x.py IN_PINS.json OUT_PINS.json W H
"""
import json
import math
import sys

PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)
OFFS = dict(M4=0.024, M5=0.024, M6=0.032, M7=0.032)
KEEP = 2.16


def face_of(p, cw, ch):
    x, y = p["x"], p["y"]
    if abs(y - (ch - 0.096)) < 1e-6:
        return "N"
    if abs(y - 0.096) < 1e-6:
        return "S"
    if abs(x - (cw - 0.096)) < 1e-6:
        return "E"
    if abs(x - 0.096) < 1e-6:
        return "W"
    raise SystemExit(f"pin {p['name']} not on a face of {cw} x {ch}")


def main(inp, outp, nw, nh):
    d = json.load(open(inp))
    m = __import__("re").search(r"outline ([0-9.]+) x ([0-9.]+)", d["frame"])
    cw, ch = float(m.group(1)), float(m.group(2))
    faces = {}
    for p in d["pins"]:
        faces.setdefault(face_of(p, cw, ch), []).append(p["name"])
    # core_pins_v37p order: per face, sorted base then bit, M5/M4 share first then M7/M6; the file keeps that order
    # per layer, so recover the face order by (layer rank, file position)
    pins, rep = [], {}
    for f in "NSEW":
        if f not in faces:
            continue
        grp = faces[f]
        L = nw if f in "NS" else nh
        lay = ["M5", "M7"] if f in "NS" else ["M4", "M6"]
        ntr = {l: int((L - 2 * KEEP) / PITCH[l]) for l in lay}
        use = [lay[0]] if len(grp) <= ntr[lay[0]] // 2 else lay
        cap = sum(ntr[l] // 2 for l in use)
        assert len(grp) <= cap, (f, len(grp), cap)
        share = [len(grp)] if len(use) == 1 else [round(len(grp) * ntr[use[0]] / (ntr[use[0]] + ntr[use[1]]))]
        if len(use) == 2:
            share.append(len(grp) - share[0])
        k0 = 0
        for l, nl in zip(use, share):
            p_, o_ = PITCH[l], OFFS[l]
            lo = math.ceil((KEEP - o_) / p_)
            hi = math.floor((L - KEEP - o_) / p_)
            for j in range(nl):
                tr = lo + int((j + 0.5) * (hi - lo + 1) / nl)
                c = round(o_ + tr * p_, 6)
                if f == "N":
                    x, y = c, round(nh - 0.096, 6)
                elif f == "S":
                    x, y = c, 0.096
                elif f == "E":
                    x, y = round(nw - 0.096, 6), c
                else:
                    x, y = 0.096, c
                pins.append(dict(name=grp[k0 + j], layer=l, x=x, y=y))
            k0 += nl
        rep[f] = dict(pins=len(grp), layers=use)
    out = dict(schema=d["schema"], core=d["core"], frame=f"core R0, origin (0,0), outline {nw:g} x {nh:g}",
               source=d["source"] + f" | v3.8x KVG3-CORES: re-spread onto {nw:g} x {nh:g} (core_pins_resize_v38x.py: "
                                    f"same faces / order / spreading rule; was {cw:g} x {ch:g})",
               faces=rep, pins=pins)
    json.dump(out, open(outp, "w"), indent=0)
    sys.stderr.write(f"{d['core']}: {len(pins)} pins {rep}\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
