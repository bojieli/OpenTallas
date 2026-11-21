"""RESET-RELAY-GEN-R3 11-21 (COORD, owner hold-fix list): auto rule for reset.root_entry_negedge.

The root entry register u_rst_in launches on the clock tap of the type's pin-register region; the first tree relay captures on
the tap of ITS region.  When the two clock insertions differ by more than THRESH_PS (150) the plain posedge->posedge hop has
a hold deficit of about the skew, and the launch-side lockup form (u_rst_in = ot_dp_rrelay_nl, falling-edge q, 0 cycles) is
needed.  Insertion per tap is a CTS result, not a plan number (a distance proxy predicts 4 % of the measured t60 skew), so the
rule reads MEASURED launch/capture latencies:

  python3 -I root_entry_scan.py report CTS_REPORT.rpt [...]          -> per report: type, launch_ps, capture_ps, skew, fires
  python3 -I root_entry_scan.py plan PLAN.json MEASURED.json OUT.json -> OUT = PLAN with reset.root_entry_negedge on every
                                                       eligible type of MEASURED {type: {launch_ps, capture_ps}} firing the rule
Types without a measurement are never flagged (UNMEASURED, not 'no').
"""
import json
import re
import sys
from pathlib import Path

THRESH_PS = 150.0
_CLK = re.compile(r"([-\d.]+)\s+\^\s+(\S+)/CLK \(")


def root_hop_latencies(rpt):
    """(launch_ps, capture_ps) of the first min-path in an OpenSTA report whose startpoint is the root entry u_rst_in, else None.
    Time column of the launch / capture flop CLK pins (source latency included as printed)."""
    for blk in re.split(r"\n(?=Startpoint:)", rpt):
        if not re.match(r"Startpoint: \S*u_rst_in\b", blk) or "Path Type: min" not in blk:
            continue
        ts = [float(m.group(1)) for m in _CLK.finditer(blk)]
        if len(ts) >= 2:
            return ts[0], ts[1]
    return None


def fires(launch_ps, capture_ps, thresh=THRESH_PS):
    return abs(capture_ps - launch_ps) > thresh


def eligible(t):
    r = t.get("reset") or {}
    return not any(r.get(k) for k in ("pin_entry_fall", "pin_entry_phase", "pin_entry_delay", "pin_root_copies", "pin_start_copies"))


def apply(raw, measured, thresh=THRESH_PS):
    """mutates raw; -> {type: skew_ps} of the types the rule turned on"""
    out = {}
    for tn, m in sorted(measured.items()):
        t = (raw.get("partition_types") or {}).get(tn)
        if t is None or not eligible(t) or not fires(m["launch_ps"], m["capture_ps"], thresh):
            continue
        t.setdefault("reset", {})["root_entry_negedge"] = True
        out[tn] = round(m["capture_ps"] - m["launch_ps"], 2)
    return out


def main(argv):
    if len(argv) >= 3 and argv[1] == "report":
        for f in argv[2:]:
            lc = root_hop_latencies(Path(f).read_text())
            if lc:
                print(f"{f}\t{lc[0]}\t{lc[1]}\t{lc[1] - lc[0]:.1f}\t{'FIRES' if fires(*lc) else 'ok'}")
        return 0
    if len(argv) == 5 and argv[1] == "plan":
        import fstart_reset_delta as F
        rb = Path(argv[2]).read_bytes()
        raw = json.loads(rb)
        dump = F.dumper(rb, raw)
        got = apply(raw, json.loads(Path(argv[3]).read_text()))
        Path(argv[4]).write_text(dump(raw))
        print(f"root_entry_negedge on {len(got)} types: {got}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
