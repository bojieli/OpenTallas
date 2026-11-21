"""RESET-RELAY-GEN-R3 11-21 (COORD, owner hold-fix list): auto rule for reset.root_entry_negedge.

The root entry register u_rst_in launches on the clock tap of the type's pin-register region; the first tree relay captures on
the tap of ITS region.  When the two clock insertions differ by more than THRESH_PS (150) the plain posedge->posedge hop has
a hold deficit of about the skew, and the launch-side lockup form (u_rst_in = ot_dp_rrelay_nl, falling-edge q, 0 cycles) is
needed.  Insertion per tap is a CTS result, not a plan number (a distance proxy predicts 4 % of the measured t60 skew), so the
rule reads MEASURED launch/capture latencies:

  python3 -I root_entry_scan.py report CTS_REPORT.rpt [...]          -> per report: status, launch_ps, capture_ps, skew, slack
  python3 -I root_entry_scan.py plan PLAN.json MEASURED.json OUT.json -> OUT = PLAN with reset.root_entry_negedge on every
                                                       eligible type of MEASURED {type: {launch_ps, capture_ps}} firing the rule
Types without a measurement are never flagged (UNMEASURED, not 'no').

POST-HOOK READ (FABLE-CLOSURE-2130, TAP-GRID-2130 canonical read): 4_cts_final.rpt shows the RAW tree depth before the tap-balance
hooks (S81 t60: 67 vs 307 ps raw, 456/438 after balance).  The rule reads 4_cts_post_hook.rpt (a path to 4_cts_final.rpt is mapped
to its sibling post-hook report) and fires only when the root-hop min path is PRESENT there with slack < 0 AND the latencies differ
by more than 150 ps.  Not listed = ABSENT: its slack is better than the last listed min path (reported as `above <slack>`), never a
fire.  A kit without a post-hook report is NOPOSTHOOK (not read).
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


def post_hook_path(path):
    """4_cts_final.rpt -> its sibling 4_cts_post_hook.rpt; any other path unchanged"""
    p = Path(path)
    return p.with_name("4_cts_post_hook.rpt") if p.name == "4_cts_final.rpt" else p


def root_hop_status(rpt):
    """dict(status, launch_ps, capture_ps, slack): status HOLD_FAIL (u_rst_in min path listed, slack < 0), HOLD_MET (listed, >= 0),
    ABSENT (not among the listed min paths; `above` = slack of the last listed min path)."""
    last = None
    for blk in re.split(r"\n(?=Startpoint:)", rpt):
        if "Path Type: min" not in blk:
            continue
        m = re.search(r"([-\d.]+)\s+slack \(", blk)
        sl = float(m.group(1)) if m else None
        if sl is not None:
            last = sl
        if not re.match(r"Startpoint: \S*u_rst_in\b", blk):
            continue
        ts = [float(x.group(1)) for x in _CLK.finditer(blk)]
        if len(ts) >= 2 and sl is not None:
            return dict(status="HOLD_FAIL" if sl < 0 else "HOLD_MET", launch_ps=ts[0], capture_ps=ts[1], slack=sl)
    return dict(status="ABSENT", above=last)


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
            pf = post_hook_path(f)
            if not pf.is_file():
                print(f"NOPOSTHOOK\t{f}")
                continue
            r = root_hop_status(pf.read_text())
            if r["status"] == "ABSENT":
                print(f"ABSENT\tabove {r['above']}\t{pf}")
            else:
                sk = r["capture_ps"] - r["launch_ps"]
                print(f"{r['status']}\t{r['launch_ps']}\t{r['capture_ps']}\t{sk:.1f}\t{r['slack']}\t{'FIRES' if r['status'] == 'HOLD_FAIL' and fires(r['launch_ps'], r['capture_ps']) else 'no'}\t{pf}")
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
