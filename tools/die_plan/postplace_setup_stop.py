"""postplace_setup_stop: end a kit after detail place when TT setup WNS is below the stop (PLACE-SETUP-STOP).

FLEET-WATCH-1630 (owner rule 11-20, cancel jobs measured unable to sign): 40 kits with post-place setup WNS below -300 ps ran CTS / GRT /
route for 114 h in 48 h and none of them could sign.  After 3_place.odb (detail place and its repair) run_kit measures the TT setup of the
placed DB (tt_setup_repair.tcl OT_TT_SETUP_MEASURE=1, OT_POSTPLACE_WORST=1) and calls this module:

  python3 -I postplace_setup_stop.py --log /work/postplace_setup.log --stop -300 --marker /work/FAIL_POSTCTS --json /work/place_setup_stop.json

exit 6 and one marker line   FAIL_POSTPLACE PLACE-SETUP-STOP wns <ps> ps < <stop> ps (TT, post-place) start=<pin> end=<pin> hop_um=<um> ...
(the kit-wave classifier reads it as class PLACE-SETUP-STOP, a plan item for the die owner's next plan event); exit 0 otherwise.  The place
ODB, reports and logs stay in the kit.  A log with no measurement never stops the flow.  Exempt rows never get the step (gen_phys
postplace_stop_ps): hold-only failures (setup is the only thing measured), lane proofs (OT_LANE / OT_PRIVATE_KIT), ECO rows (OT_ECO),
rows flagged keep_going (OT_KEEP_GOING=1) and OT_POSTPLACE_SETUP_STOP=0.

FLOW-PLACEMEAS-1121 (FABLE-PD-QC-0840 items 1 / 4): the measured number is data setup only.  Reset recovery / removal (unbuffered
reset nets at place) is read from its own OT_POSTPLACE_RECOVERY line into the record (recovery_wns / recovery_start / recovery_end)
and never stops the kit; port-direct macro clocks (fclk_in_* -> landing macro) are timed propagated in the tcl.  The -300 stop is unchanged."""
import argparse
import json
import re
import sys

WNS_RE = re.compile(r"OT_TT_SETUP_REPAIR\s+measure\s+TT setup wns\s+(-?[0-9.]+(?:[eE][-+]?[0-9]+)?)")
WORST_RE = re.compile(r"OT_POSTPLACE_WORST\s+start=(\S+)\s+end=(\S+)\s+hop_um=(\S+)")
RECOV_RE = re.compile(r"OT_POSTPLACE_RECOVERY\s+wns\s+(-?[0-9.]+(?:[eE][-+]?[0-9]+)?)\s+start=(\S+)\s+end=(\S+)")


def read_log(text):
    """-> dict(wns, start, end, hop_um); wns None when the log has no measurement"""
    m = WNS_RE.findall(text)
    w = WORST_RE.findall(text)
    rv = RECOV_RE.findall(text)
    out = dict(wns=float(m[-1]) if m else None, start="?", end="?", hop_um=None, recovery_wns=None, recovery_start=None, recovery_end=None)
    if w:
        out.update(start=w[-1][0], end=w[-1][1], hop_um=None if w[-1][2] in ("?", "nan") else float(w[-1][2]))
    if rv:
        out.update(recovery_wns=float(rv[-1][0]), recovery_start=rv[-1][1], recovery_end=rv[-1][2])
    return out


def decide(text, stop_ps):
    """-> (stop?, marker line, record)"""
    r = read_log(text)
    r["stop_ps"] = float(stop_ps)
    if r["wns"] is None or not r["wns"] < float(stop_ps):
        return False, "", r
    hop = "?" if r["hop_um"] is None else f"{r['hop_um']:.1f}"
    line = (f"FAIL_POSTPLACE PLACE-SETUP-STOP wns {r['wns']:.2f} ps < {float(stop_ps):.0f} ps (TT, post-place; routing cannot close it) "
            f"start={r['start']} end={r['end']} hop_um={hop}; place ODB, reports and logs kept (plan item for the die owner)")
    return True, line, r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--stop", type=float, default=-300.0)
    ap.add_argument("--marker")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    try:
        text = open(a.log, errors="replace").read()
    except OSError:
        text = ""
    stop, line, rec = decide(text, a.stop)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(dict(rec, stopped=stop), f, indent=1)
            f.write("\n")
    if stop:
        print(line)
        if a.marker:
            with open(a.marker, "a") as f:
                f.write(line + "\n")
        return 6
    print("OT_POSTPLACE_SETUP_STOP pass" if rec["wns"] is not None else "OT_POSTPLACE_SETUP_STOP no measurement, flow continues")
    if rec["recovery_wns"] is not None:
        print(f"OT_POSTPLACE_RECOVERY reported wns {rec['recovery_wns']:.2f} ps start={rec['recovery_start']} end={rec['recovery_end']} "
              "(reset recovery before the reset tree; not a setup stop)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
