#!/usr/bin/env python3
"""Clock duty/MPW report using measured source edges and the shared clock calibration.

Raw input needs OT_EDGES v1, or explicit --format legacy for historical
F port fall_late rise_late slew rows. Mixed paths require a component proof JSON.
This reports phase widths, not a related-pair timing or die-freeze verdict.
"""
import argparse
import json
import math
import statistics
from pathlib import Path

import die_sta_related as D

# Inherited DFFHQNx1 TT worst 'when' arc table; retained conservatively for FF.
IDX = [5, 10, 20, 40, 80, 160, 320]
MPW = [39.99, 42.25, 42.25, 45.32, 80.57, 161.13, 321.05]


def mpw(slew):
    if slew <= IDX[0]:
        return MPW[0]
    for i in range(len(IDX) - 1):
        if slew <= IDX[i + 1]:
            f = (slew - IDX[i]) / (IDX[i + 1] - IDX[i])
            return MPW[i] + f * (MPW[i + 1] - MPW[i])
    return MPW[-1]


def read_raw(path, fmt="auto"):
    lines = Path(path).read_text().splitlines()
    versioned = any(line.startswith("# OT_EDGES v1") for line in lines[:5])
    if fmt == "legacy" and versioned:
        raise ValueError("legacy format conflicts with OT_EDGES v1 header")
    if fmt == "v1" and not versioned:
        raise ValueError("v1 requires OT_EDGES v1 header")
    if fmt == "auto" and not versioned:
        raise ValueError("ambiguous unversioned edge rows: specify --format legacy")
    rows = {"T": {}, "F": {}}
    for line in lines:
        x = line.split()
        if not x or x[0] not in rows:
            continue
        if len(x) != 5:
            raise ValueError("invalid measured edge row: " + line)
        values = list(map(float, x[2:]))
        if not all(math.isfinite(v) for v in values):
            raise ValueError("nonfinite measured edge row")
        if x[1] in rows[x[0]]:
            raise ValueError("duplicate edge row: " + x[1])
        rows[x[0]][x[1]] = values
    if not rows["T"] or rows["T"].keys() != rows["F"].keys():
        raise ValueError("missing measured rise/fall tap rows")
    taps = []
    for port, t in rows["T"].items():
        f = rows["F"][port]
        if not versioned and abs(t[0] - f[1]) > .03:
            raise ValueError("legacy F rise arrival disagrees with T row: " + port)
        # Legacy F's second field is rise_late, never fall_early.
        taps.append(dict(port=port, late_ps=t[0], early_ps=t[1], fall_late_ps=f[0],
                         fall_early_ps=f[1] if versioned else t[1]+f[0]-f[1],
                         slew_ps=max(t[2] if len(t)>2 else 0., f[2] if len(f)>2 else 0.)))
    return taps, "v1" if versioned else "legacy"


def report(path, corner, clock_cell, fmt="auto", period=833., clock_cal="spice_edge"):
    if corner not in ("TT", "FF"):
        raise ValueError("duty closure corners are TT/FF")
    if clock_cell not in ("buf", "inv", "inv2", "mixed"):
        raise ValueError("declare clock_cell buf/inv/inv2/mixed")
    if not math.isfinite(period) or period <= 0:
        raise ValueError("period must be finite and positive")
    if clock_cal not in ("spice", "spice_edge", "spice_buf_edge", "spice_cell"):
        raise ValueError("unknown shared clock calibration")
    if Path(path).suffix == ".json":
        proof = json.loads(Path(path).read_text())
        if proof.get("corner", corner) != corner:
            raise ValueError("proof corner differs from requested corner")
        taps, basis = proof["taps"], "component-proof" if proof.get("clock_components_basis") else "proof"
        if proof.get("clock_cal_components"):
            raise ValueError("input must be raw; already calibrated components")
    else:
        taps, basis = read_raw(path, fmt)
        proof = {}
    if not taps or len({t["port"] for t in taps}) != len(taps):
        raise ValueError("empty or duplicate tap proof")
    if clock_cell == "mixed" and not proof.get("clock_components_basis"):
        raise ValueError("mixed clock requires measured per-master components")
    normalized = "inv" if clock_cell == "inv2" else clock_cell
    rows = []
    for tap in taps:
        for key in ("late_ps", "early_ps", "fall_late_ps", "fall_early_ps"):
            if key not in tap or not math.isfinite(float(tap[key])):
                raise ValueError("missing/nonfinite measured both-edge field: " + key)
        masters = set(tap.get("clock_masters", proof.get("clock_masters", [])))
        expected = set(D.CLOCK_CELL_MASTERS.get(normalized, ()))
        if masters and not masters <= expected and not proof.get("clock_components_basis"):
            raise ValueError("heterogeneous clock masters require components")
        if proof.get("clock_components_basis"):
            if clock_cal not in ("spice_edge", "spice_cell"):
                raise ValueError("component proofs require spice_edge or spice_cell")
            from clock_components import scaled
            v = scaled(tap.get("clock_components"), tap, corner, clock_cal)
        else:
            _, scaled_taps = D.apply_clock_cal({}, {tap["port"]: tap}, corner, normalized, clock_cal,
                                              proof=Path(path).parent)
            v = scaled_taps[tap["port"]]
        high = period/2 + v["fall_late_ps"] - v["late_ps"]
        low = period - high
        if "slew_ps" not in tap:
            raise ValueError("measured tap slew required for MPW")
        slew = float(tap["slew_ps"])
        if not math.isfinite(slew) or slew < 0:
            raise ValueError("invalid slew")
        rows.append(dict(port=tap["port"], duty=high/period, high_ps=high, low_ps=low, mpw_ps=mpw(slew)))
    duty = [r["duty"] for r in rows]
    return dict(taps=len(rows), duty_min=min(duty), duty_med=statistics.median(duty), duty_max=max(duty),
                outside_45_55=sum(not .45 <= d <= .55 for d in duty),
                mpw_fail=sum(min(r["high_ps"], r["low_ps"]) < r["mpw_ps"] for r in rows),
                worst=sorted(rows, key=lambda r: -abs(r["duty"]-.5))[:5],
                basis=basis, clock_cell=clock_cell, clock_cal=clock_cal, period_ps=period,
                phase_basis="calibrated measured late fall minus late rise; not an OCV pulse bound")


def add_arguments(ap):
    ap.add_argument("arr_tt"); ap.add_argument("arr_ff"); ap.add_argument("out")
    ap.add_argument("--clock-cell", required=True, choices=("buf", "inv", "inv2", "mixed"))
    ap.add_argument("--format", default="auto", choices=("auto", "v1", "legacy"))
    ap.add_argument("--clock-cal", default="spice_edge", choices=("spice", "spice_edge", "spice_buf_edge", "spice_cell"))
    ap.add_argument("--period", type=float, default=833.)


def run(a):
    corners = {c: report(p, c, a.clock_cell, a.format, a.period, a.clock_cal)
               for c, p in (("TT", a.arr_tt), ("FF", a.arr_ff))}
    result = dict(rule="duty45-55%, both phases >= inherited DFFHQNx1 TT MPW table", corners=corners)
    Path(a.out).write_text(json.dumps(result, indent=1)+"\n")
    print(json.dumps({c: {k: v for k, v in r.items() if k != "worst"} for c, r in corners.items()}))
    return 1 if any(r["outside_45_55"] or r["mpw_fail"] for r in corners.values()) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    add_arguments(ap)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
