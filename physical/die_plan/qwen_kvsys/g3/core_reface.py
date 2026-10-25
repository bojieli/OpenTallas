#!/usr/bin/env python3
"""KV-PLAN2 10-25 (plan v3.9d): re-face the pins of PLANNED hard cores that were moved inside their type.

geom_v39d.py re-places the 22 kv3_hub_Wi host cores (none hardened: 0 kits; their pins also change under BRIEFING 16a,
host logic on the die clock).  Their v3.7p pin files chose faces for the old row placement, so G0C core_faces finds
ports facing away from their partners.  This pass takes check.py core_faces' own verdict (same connectivity, same cos
score, its 're-pin to face F' hint) for every FAILing port of the listed types, moves that port's pins to face F, and
re-spreads every touched face evenly over the face (2.16-um corner keep-out) on the plan tracks: E/W faces M4 y-tracks
(spill M6), N/S faces M5 x-tracks (spill M7), <= 1 pin per 2 tracks per layer, as core_pins_v37p.py.  A pins file
shared by several instances (qkd_hr_phy_adp x8, mixed orients) is re-faced only when every instance's hint agrees.
usage: core_reface.py PLAN.json --types kv3_hub_Wi [--rounds 2]
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(R / "tools/die_plan"))
import check  # noqa: E402
import schema as S  # noqa: E402

PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)
OFFS = dict(M4=0.024, M5=0.024, M6=0.032, M7=0.032)
KEEP = 2.16
LAY = dict(N=("M5", "M7"), S=("M5", "M7"), E=("M4", "M6"), W=("M4", "M6"))
MSG = re.compile(r"type (\S+) core (\S+) port (\S+): .*\(re-pin to face ([NSEW])\)")
# type-frame face -> core-frame face for a core orient (involution, as check._core_face)


def core_face_of(o, f):
    if o in ("MX", "R180") and f in "NS":
        return "S" if f == "N" else "N"
    if o in ("MY", "R180") and f in "EW":
        return "W" if f == "E" else "E"
    return f


def spread_face(pins, f, cw, ch):
    """re-place the pins of one core face evenly on the plan tracks; pins keep their order along the face."""
    L = ch if f in "EW" else cw
    along = (lambda p: p["y"]) if f in "EW" else (lambda p: p["x"])
    pins.sort(key=along)
    l0, l1 = LAY[f]
    cap = []
    for ln in (l0, l1):
        p_, o_ = PITCH[ln], OFFS[ln]
        k0 = int((KEEP - o_) / p_) + 1
        k1 = int((L - KEEP - o_) / p_)
        cap.append((ln, [round(o_ + k * p_, 6) for k in range(k0, k1 + 1)]))
    # one layer while it holds <= 1 pin per 2 tracks, else bits interleaved over both (M4/M6 or M5/M7)
    groups = [(cap[0], pins)] if len(pins) <= len(cap[0][1]) // 2 else [(cap[0], pins[0::2]), (cap[1], pins[1::2])]
    out = []
    for (ln, tracks), ps in groups:
        m = len(ps)
        if m > len(tracks) // 2 + 1:
            raise ValueError(f"face {f}: {m} pins on {ln} > half of {len(tracks)} tracks")
        for j, p in enumerate(ps):
            t = tracks[int((j + 0.5) * len(tracks) / m)]
            q = dict(p, layer=ln)
            if f in "EW":
                q["y"], q["x"] = t, (0.0 if f == "W" else cw)
            else:
                q["x"], q["y"] = t, (0.0 if f == "S" else ch)
            out.append(q)
    return out


def face_of_pin(p, cw, ch):
    return min([(p["x"], "W"), (cw - p["x"], "E"), (p["y"], "S"), (ch - p["y"], "N")])[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--types", nargs="+", required=True)
    ap.add_argument("--rounds", type=int, default=2)
    a = ap.parse_args()
    pd = Path(a.plan).resolve().parent
    total = 0
    for rnd in range(a.rounds):
        raw = S.load(a.plan)
        P = S.Plan(raw, Path(a.plan).resolve())
        Rp = check.Report(completeness=True)
        check._PIN_CACHE.clear()
        check.check_core_faces(P, Rp, plan_dir=pd, max_msgs=10 ** 6)
        hints = defaultdict(dict)          # pins_file -> {port: set(core-frame face)}
        files = {}
        for f in Rp.items:
            if f["level"] != "ERROR":
                continue
            m = MSG.match(f["msg"])
            if not m or m.group(1) not in a.types:
                continue
            tn, ci, lp, tf = m.groups()
            hc = next(c for c in P.types[tn]["hard_cores"] if c["inst"] == ci)
            files[hc["pins_file"]] = hc
            hints[hc["pins_file"]].setdefault(lp, set()).add(core_face_of(hc.get("orient", "R0"), tf))
        moved = 0
        for pf, ports in hints.items():
            hc = files[pf]
            fn = pd / pf
            d = json.loads(fn.read_text())
            cw, ch = hc["outline_um"]
            byface = defaultdict(list)
            touched = set()
            for p in d["pins"]:
                base = p["name"].split("[")[0]
                f0 = face_of_pin(p, cw, ch)
                h = ports.get(base)
                if h and len(h) == 1 and next(iter(h)) != f0:
                    f1 = next(iter(h))
                    touched.update((f0, f1))
                    byface[f1].append(dict(p))
                    moved += 1
                else:
                    byface[f0].append(dict(p))
            pins = []
            for f, ps in byface.items():
                pins += spread_face(ps, f, cw, ch) if f in touched else ps
            d["pins"] = pins
            d["source"] = d.get("source", "") + " | KV-PLAN2 v3.9d core_reface.py (core re-placed in hub_Wi)"
            fn.write_text(json.dumps(d, indent=0) + "\n")
        print(f"core_reface round {rnd}: {sum(len(v) for v in hints.values())} ports hinted, {moved} pins moved")
        total += moved
        if not moved:
            break


if __name__ == "__main__":
    main()
