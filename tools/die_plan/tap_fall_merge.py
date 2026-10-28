#!/usr/bin/env python3
"""FLOW-ONEMODEL-1: put the MEASURED falling-edge clock arrival into a die clock proof (tap_arrivals_<C>.json), so
count_align_plan (--sta-proof) and die_sta_related (--count-align) time every fall-edge sample on it.

    tap_fall_merge.py PROOF_DIR CORNER DUTY_TXT --out OUT_DIR

DUTY_TXT = a both-edge clock-only STA readout of the SAME built clock (one line per tap; the two forms in use):
    D <port> <rise_ps> <fall_ps> [slews...]      (DIE-KV-11 duty.sh)
    F <port> <fall_ps> <rise_ps> [slew]          (DIE-QC-11 / DIE-S81-12 mk_clkfirst duty readout)
    <port> <rise_ps> <fall_ps>                   (plain)
fall_ps is the clock pin's falling-edge arrival measured from the source's falling edge (so the sampling instant is
T/2 + fall_ps).  Per tap the distortion delta = fall - rise of the readout is added to the proof's own late/early:
fall_late_ps = late_ps + delta, fall_early_ps = early_ps + delta (the proof's late/early pin-cap spread is kept; the
readout and the proof may differ by a global scale, delta is what moves the edge).  A tap missing from the readout
gets no fall arrival, so a fall sample on it fails closed (never rise + T/2).  Tree-node fall arrivals are not in the
readouts: start retime flops on tree nodes (virtual taps) stay rise-only.  Other proof files are copied unchanged."""
import argparse
import json
import shutil
import sys
from pathlib import Path


def read_duty(path):
    out = {}
    for ln in Path(path).read_text().splitlines():
        f = ln.split()
        if len(f) < 3 or f[0].startswith("#"):
            continue
        try:
            if f[0] == "D":
                port, rise, fall = f[1], float(f[2]), float(f[3])
            elif f[0] == "F":
                port, fall, rise = f[1], float(f[2]), float(f[3])
            else:
                port, rise, fall = f[0], float(f[1]), float(f[2])
        except (IndexError, ValueError):
            continue
        out[port] = (rise, fall)
    return out


def merge(doc, duty):
    n = 0
    dl = []
    for t in doc["taps"]:
        x = duty.get(t["port"])
        for k in ("fall_late_ps", "fall_early_ps"):
            t.pop(k, None)
        if x is None:
            continue
        d = x[1] - x[0]
        t["fall_late_ps"] = float(t["late_ps"]) + d
        t["fall_early_ps"] = float(t["early_ps"]) + d
        if "abs_late_ps" in t:
            t["abs_fall_late_ps"], t["abs_fall_early_ps"] = float(t["abs_late_ps"]) + d, float(t["abs_early_ps"]) + d
        n += 1
        dl.append(d)
    dl.sort()
    doc["fall_arrivals"] = dict(source="FLOW-ONEMODEL-1 tap_fall_merge.py", taps_with_fall=n, taps=len(doc["taps"]),
                                fall_minus_rise_ps=dict(min=dl[0], median=dl[len(dl) // 2], max=dl[-1]) if dl else None)
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proof")
    ap.add_argument("corner")
    ap.add_argument("duty")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    src, out = Path(a.proof), Path(a.out)
    if src.resolve() == out.resolve():
        ap.error("--out must differ from the proof dir (the signed proof is never rewritten in place)")
    out.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file() and not (out / f.name).exists():
            shutil.copy2(f, out / f.name)
    name = f"tap_arrivals_{a.corner}.json"
    doc = merge(json.loads((src / name).read_text()), read_duty(a.duty))
    (out / name).write_text(json.dumps(doc))
    fa = doc["fall_arrivals"]
    print(json.dumps(dict(corner=a.corner, **fa)))
    return 0 if fa["taps_with_fall"] else 1


if __name__ == "__main__":
    sys.exit(main())
