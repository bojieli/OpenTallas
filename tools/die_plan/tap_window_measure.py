#!/usr/bin/env python3
"""tap_window_measure.py: per-port kit tap windows from the AS-BUILT tap trees of a kit (S81-COL-CLK-1116, spec 0b).

    tap_window_measure.py --type T (--log 4_1_cts.log | --odb-out TAPRC.txt) [--floor 10] [--cap 40] [--out rows.json]

Why: a flat clock.tap_window.window_ps (165 ps on col_h9_r2) charges every grid port and core tap the same early/late range
in the kit SDC, setup and hold, although the as-built trees measure far less (CTS: TT 6,543 endpoints / -340.6 with the
window, 26 / -175.6 without).  The kit window models the per-tap uncertainty of the delivered tap arrival, so it is measured
here from the kit's own CTS result: for each clock port (grid tap clk, clk_t<N>; core taps clk_c<k>; tap_balance.tcl
statistics: mean, min, max sink insertion on the active edge, sink count) the window is

    D_p = ceil( max(floor, (max_p - min_p) / 2) )          (R-CLOCK-7 tolerance u: half the tap's own sink range, >= floor)

(single-sink taps measure range 0 and take the floor).  Input is the `OT_TAP_BALANCE itN ...` / `OT_TAP_RC mean(min-max,sinks)`
line of the kit's CTS log (last one wins) or the OT_TAP_RC output of tap_window_measure.tcl run on a 4_cts.odb.  Output is the
plan row clock.tap_window.per_port_ps[T] = {port: D_p} (gen_phys.tap_window_port_table, [0, T/4]) plus a summary on stdout:
mean spread of the taps, the window distribution and the ports above --cap.  Rows only: DIE-S81-92 folds them into the plan.
"""
import argparse
import json
import math
import re
import sys

LINE = re.compile(r"^OT_TAP_(?:BALANCE(?: GRT)? it\d+ target \d+|RC mean\(min-max,sinks\)):\s*(.*)$")
ENT = re.compile(r"(\S+?)=(-?[\d.]+)\((-?[\d.]+)-(-?[\d.]+),(\d+)\)")


def last_tap_line(text):
    last = None
    for ln in text.splitlines():
        m = LINE.match(ln.strip())
        if m:
            last = m[1]
    return last


def parse_taps(line):
    """{port: dict(mean, min, max, sinks)}"""
    return {n: dict(mean=float(a), min=float(b), max=float(c), sinks=int(k)) for n, a, b, c, k in ENT.findall(line)}


def windows(taps, floor=10.0):
    return {p: int(math.ceil(max(floor, (t["max"] - t["min"]) / 2.0))) for p, t in sorted(taps.items())}


def summary(taps, win, cap):
    means = [t["mean"] for t in taps.values()]
    ws = sorted(win.values())
    q = lambda f: ws[min(len(ws) - 1, int(f * len(ws)))]
    over = {p: w for p, w in win.items() if w > cap}
    return dict(ports=len(taps), mean_lo=min(means), mean_hi=max(means), mean_spread=max(means) - min(means),
                window_min=ws[0], window_p50=q(0.5), window_p90=q(0.9), window_max=ws[-1], cap=cap, over_cap=over)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", required=True)
    ap.add_argument("--log", help="kit 4_1_cts.log (or any file holding OT_TAP_BALANCE / OT_TAP_RC lines)")
    ap.add_argument("--floor", type=float, default=10.0)
    ap.add_argument("--cap", type=float, default=40.0)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    line = last_tap_line(open(a.log).read())
    if not line:
        print("tap_window_measure: no OT_TAP_BALANCE / OT_TAP_RC line in", a.log, file=sys.stderr)
        return 2
    taps = parse_taps(line)
    win = windows(taps, a.floor)
    row = {a.type: win}
    if a.out:
        json.dump({"clock.tap_window.per_port_ps": row}, open(a.out, "w"), indent=1)
    print(json.dumps(summary(taps, win, a.cap)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
