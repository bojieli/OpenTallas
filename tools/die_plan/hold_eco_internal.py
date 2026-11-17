#!/usr/bin/env python3
"""hold_eco_internal.py -- sizing + gate of the post-route INTERNAL-endpoint hold stage (HOLD-FLOW-R 11-16, closure lever 1).

Why: pre-route hold repair closes to 0 on the GRT estimate and extraction then moves short paths by 9-17 ps, so every
route ends with internal FF hold of -9 .. -69 ps on 6 .. 858 endpoints (QC coll_n / W0 / H16 / H17 / P3, HEAD hw4 / host_e,
S81 halves) while those endpoints keep 170-430 ps of TT setup room.  Proven by hand on QC coll_n: 80 HB4 cells at 64 capture
pins, 144 nets re-routed, DRC 0, TT -1.39, FF hold -58.19 -> +0.47.  This file is the generic form.

  plan  ENDPOINTS.tsv OUT.tsv   size the insert per capture pin (target +10 ps, not 0)
  gate  BEFORE.json AFTER.json  accept / refuse the stage result (DRC 0, TT >= -42, internal FF hold >= 0)

ENDPOINTS.tsv (written by hold_eco_internal_dump.tcl, header line required), tab separated:
  endpoint  startpoint  start_kind  end_kind  ff_hold_slack_ps  tt_setup_slack_ps
kind is reg | port | macro.  Only reg/macro starts to a reg capture pin (D, RESETN, SETN, wd_in*) are internal; a path that
starts at an input port or ends at an output port is the parent's and never gets a cell (no port-only padding).
OUT.tsv (read by hold_eco_internal_insert.tcl via OT_PRD_HOLD_PLAN): capture_pin<TAB>n_hb4, then a comment trailer.
Sizing: need = target - slack.  One HB4 covers need <= DOUBLE_OVER_PS (25), else ceil(need / HB4_FF_PS) and at least two.
Each HB4 costs HB4_TT_MAX_PS of TT setup; an endpoint whose TT slack minus that cost would fall under TT_FLOOR_PS (-42, the
gate) is skipped and listed, never silently dropped.
"""
import json
import math
import sys

TARGET_PS = 10.0          # hold repair target; the gate stays FF hold >= 0
HB4_FF_PS = 37.0          # FF delay of one HB4xp67 (measured 11-15 s81hc ref: ~37 ps)
HB4_TT_MAX_PS = 171.24    # TT delay of one HB4xp67 at slew <= 320 (coll_n pilot)
DOUBLE_OVER_PS = 25.0     # need above this gets two cells at least
MAX_PER_ENDPOINT = 4
TT_FLOOR_PS = -42.0       # gate: routed TT WNS >= -42
CAPTURE_PINS = ("D", "RESETN", "SETN")
KINDS = ("reg", "port", "macro")


def capture_pin(endpoint):
    """True for a flop capture pin the inserter supports"""
    pin = endpoint.rsplit("/", 1)[-1]
    return pin in CAPTURE_PINS or pin.startswith("wd_in")


def need_to_cells(need, hb4_ff=HB4_FF_PS, double_over=DOUBLE_OVER_PS, cap=MAX_PER_ENDPOINT):
    if need <= 0:
        return 0
    n = math.ceil(need / hb4_ff)
    if need > double_over:
        n = max(n, 2)
    return min(max(n, 1), cap)


def read_endpoints(text):
    rows = []
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not lines or lines[0].split("\t")[0] != "endpoint":
        raise ValueError("endpoints file needs the header line: endpoint startpoint start_kind end_kind ff_hold_slack_ps tt_setup_slack_ps")
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) != 6:
            raise ValueError(f"bad endpoint row (6 tab fields): {ln!r}")
        e, s, sk, ek, ff, tt = f
        if sk not in KINDS or ek not in KINDS:
            raise ValueError(f"bad kind in {ln!r}")
        ffv, ttv = float(ff), float(tt)
        if not (math.isfinite(ffv) and math.isfinite(ttv)):
            raise ValueError(f"non finite slack in {ln!r}")
        rows.append(dict(endpoint=e, startpoint=s, start_kind=sk, end_kind=ek, ff=ffv, tt=ttv))
    return rows


def plan(rows, target=TARGET_PS, hb4_ff=HB4_FF_PS, hb4_tt=HB4_TT_MAX_PS, tt_floor=TT_FLOOR_PS,
         double_over=DOUBLE_OVER_PS, cap=MAX_PER_ENDPOINT):
    """-> {cells: [(capture_pin, n)], skipped: [(endpoint, reason)], summary}.  The worst path to a pin sets its need."""
    worst = {}
    skipped = []
    for r in rows:
        e = r["endpoint"]
        if r["start_kind"] == "port" or r["end_kind"] == "port":
            skipped.append((e, "port path: the parent's, no cell"))
            continue
        if not capture_pin(e):
            skipped.append((e, "not a supported capture pin (D/RESETN/SETN/wd_in*)"))
            continue
        if r["ff"] >= target:
            continue
        cur = worst.get(e)
        if cur is None or r["ff"] < cur["ff"]:
            worst[e] = r
    cells = []
    for e in sorted(worst):
        r = worst[e]
        n = need_to_cells(target - r["ff"], hb4_ff, double_over, cap)
        if r["tt"] - n * hb4_tt < tt_floor:
            skipped.append((e, f"TT slack {r['tt']:.2f} - {n} x {hb4_tt:g} < {tt_floor:g}"))
            continue
        cells.append((e, n))
    total = sum(n for _, n in cells)
    return dict(cells=cells, skipped=skipped, summary=dict(
        endpoints=len(cells), hb4=total, skipped=len(skipped), target_ps=target,
        worst_ff_ps=min([r["ff"] for r in worst.values()] or [0.0]),
        selected_over_negative=f"{len(cells)} of {sum(1 for r in rows if r['ff'] < 0 and r['start_kind'] != 'port' and r['end_kind'] != 'port')}"))


def write_plan(p, out):
    with open(out, "w") as f:
        f.write("# hold_eco_internal plan: capture_pin\tn_hb4\n")
        for e, n in p["cells"]:
            f.write(f"{e}\t{n}\n")
        for e, why in p["skipped"]:
            f.write(f"# skipped {e}: {why}\n")
        f.write("# summary " + json.dumps(p["summary"], sort_keys=True) + "\n")


def read_plan(text):
    out = []
    for ln in text.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        e, n = ln.split("\t")
        if int(n) < 1 or not capture_pin(e):
            raise ValueError(f"bad plan row {ln!r}")
        out.append((e, int(n)))
    return out


def gate(before, after, tt_floor=TT_FLOOR_PS):
    """before / after: {drc, tt_wns_ps, ff_internal_wns_ps, ff_internal_endpoints}.  -> (ok, [why])"""
    why = []
    if int(after["drc"]) != 0:
        why.append(f"DRC {after['drc']} != 0")
    if float(after["tt_wns_ps"]) < tt_floor:
        why.append(f"TT WNS {after['tt_wns_ps']} < {tt_floor:g}")
    if float(after["ff_internal_wns_ps"]) < 0:
        why.append(f"internal FF hold {after['ff_internal_wns_ps']} < 0 on {after.get('ff_internal_endpoints')} endpoints")
    if before is not None and float(after["ff_internal_wns_ps"]) < float(before["ff_internal_wns_ps"]):
        why.append("internal FF hold got worse")
    return not why, why


def main(argv):
    if len(argv) >= 4 and argv[1] == "plan":
        rows = read_endpoints(open(argv[2]).read())
        p = plan(rows)
        write_plan(p, argv[3])
        print(json.dumps(p["summary"], sort_keys=True))
        return 0
    if len(argv) == 4 and argv[1] == "gate":
        ok, why = gate(json.load(open(argv[2])), json.load(open(argv[3])))
        print("HOLD_ECO_INTERNAL " + ("PASS" if ok else "FAIL " + "; ".join(why)))
        return 0 if ok else 1
    print(__doc__.split("\n\n")[0], file=sys.stderr)
    print("usage: hold_eco_internal.py plan ENDPOINTS.tsv OUT.tsv | gate BEFORE.json AFTER.json", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
