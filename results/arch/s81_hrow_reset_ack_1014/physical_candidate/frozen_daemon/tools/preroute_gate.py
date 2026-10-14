#!/usr/bin/env python3
"""Pre-route timing gate (OWNER 2026-10-08, stream preroute-gate): stop a route whose placed design is far from closing
BEFORE CTS / global route / detail route are spent on it.

tools/preroute_gate.tcl dumps, at ORFS POST DETAIL_PLACE (resizer repair_design + detailed placement done, ideal clocks,
placement parasitics, TT libraries under option B), the setup slack of every endpoint's worst path down to +300 ps,
binned per path class:
  reg2reg  register -> register (std-cell sequentials, incl. recovery/removal checks)
  macro    a macro (BLOCK master: ROM / SRAM / hardened sub-block) at either end, no port
  io       a block port at either end (judged against the die-link budget: reported, never gated, the IO budget and the
           clock insertion are not final before CTS)
This file judges the dump.  Slack is normalised to the 833.333 ps sign-off (route at 730-833 ps: + (833.333 - period)).

FAIL (verdict PREROUTE_MARGIN) when, for a gated class (reg2reg, macro), the normalised WNS < ws_ps AND more than
count endpoints sit wholly below ws_ps.  The owner's design intent is "+250 ps per stage pre-route"; the calibration on
2026-10-08's finished TT routes (tools/closure_loop/preroute_offline.sh, preroute-gate.log) showed post-placement slack
recovers by hundreds of ps (blocks closed from -737 ps post-place), so the thresholds below sit under the worst
eventual closure (THRESHOLDS): the gate never rejects a variant that would have closed.  The +250 ps line is reported as the
design-margin view (endpoints below it per class), not judged.

    preroute_gate.py check DUMP.json [--out REPORT.json] [--set key=value ...] [--warn-only] [--dump-ms N]
    preroute_gate.py table DUMP.json ...         # per-class metrics (calibration rows), no verdict
Exit: 0 PASS, 3 FAIL (prints PREROUTE_MARGIN: ...), 2 tool error.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

SIGNOFF_PS = 833.333
GATED = ("reg2reg", "macro")
CLASSES = ("reg2reg", "macro", "io")

THRESHOLDS = {
    # calibrated 2026-10-08 on 189 finished routes (172 closed at TT): the worst eventual closure placed at -314.9 ps
    # (gate metric; -736.6 in ORFS's own place report, ha2_truecredit_tx_reg), so -750 rejects none of them; the one
    # route it stops (hbm_hc_quarter, macro WNS -1859, 10,066 endpoints below) spent 11.9 h to end at TT -3474.
    "ws_ps": -750.0,           # normalised WNS bound (below the worst eventual closure, in both metrics)
    "count": 50,               # ... with more endpoints wholly below it (one stray path never stops a route)
    "design_margin_ps": 250.0,  # owner's design-margin view: endpoints below it are REPORTED per class (no verdict)
}


def shift(period):
    """route-period slack -> sign-off (833.333) slack for the 1.2 GHz domain; another clock signs off at its own period"""
    if period is None:
        return 0.0
    return SIGNOFF_PS - period if 700.0 <= period <= SIGNOFF_PS + 0.5 else 0.0


def below(hist, bin_ps, sh, thr):
    """endpoints whose normalised slack is WHOLLY below thr (a bin counts only when its upper edge is <= thr: the
    histogram never pushes the count past what really failed)"""
    return sum(int(n) for b, n in hist.items() if (int(b) + 1) * bin_ps + sh <= thr)


def metrics(dump, thr=None):
    th = dict(THRESHOLDS, **(thr or {}))
    sh = shift(dump.get("period_ps"))
    bin_ps = float(dump.get("bin_ps") or 25.0)
    out = {}
    for cls in CLASSES:
        c = (dump.get("classes") or {}).get(cls) or {}
        ws = c.get("ws_ps")
        h = c.get("hist") or {}
        out[cls] = dict(
            ws_ps=None if ws is None else round(ws + sh, 1), raw_ws_ps=ws,
            endpoints_le_cap=int(c.get("endpoints") or 0),
            below_gate=below(h, bin_ps, sh, th["ws_ps"]),
            below_0=below(h, bin_ps, sh, 0.0),
            below_design_margin=below(h, bin_ps, sh, th["design_margin_ps"]),
            worst=(c.get("worst") or [])[:3])
    return out, sh


def judge(dump, thr=None):
    """(verdict 'PASS'|'FAIL', reasons[], metrics) of one dump"""
    th = dict(THRESHOLDS, **(thr or {}))
    m, sh = metrics(dump, th)
    reasons = []
    for cls in GATED:
        x = m[cls]
        if x["ws_ps"] is not None and x["ws_ps"] < th["ws_ps"] and x["below_gate"] > th["count"]:
            w = (x["worst"] or [{}])[0]
            reasons.append(f"{cls} WNS {x['ws_ps']:+.1f} ps at 833.333 (route-period {x['raw_ws_ps']:+.1f}), "
                           f"{x['below_gate']} endpoints below {th['ws_ps']:g} (> {th['count']}); worst "
                           f"{w.get('start', '?')} -> {w.get('end', '?')}")
    if dump.get("truncated"):
        # a truncated enumeration under-counts: never fail on a count it could not see in full (only the ws is exact)
        pass
    return ("FAIL" if reasons else "PASS"), reasons, m


def summary_line(m):
    return "; ".join(f"{c} ws {m[c]['ws_ps'] if m[c]['ws_ps'] is not None else 'n/a'} ps, <0: {m[c]['below_0']}, "
                     f"<+{THRESHOLDS['design_margin_ps']:g}: {m[c]['below_design_margin']}" for c in CLASSES)


def parse_set(items):
    out = {}
    for s in items or []:
        k, v = s.split("=", 1)
        if k not in THRESHOLDS:
            raise SystemExit(f"preroute_gate: unknown threshold {k}")
        out[k] = float(v)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("dump")
    c.add_argument("--out")
    c.add_argument("--set", action="append")
    c.add_argument("--warn-only", action="store_true")
    c.add_argument("--dump-ms", type=float)
    t = sub.add_parser("table")
    t.add_argument("dumps", nargs="+")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "table":
            for d in a.dumps:
                m, sh = metrics(json.loads(Path(d).read_text()))
                print(json.dumps(dict(dump=d, shift_ps=sh, **{k: {kk: vv for kk, vv in v.items() if kk != "worst"}
                                                              for k, v in m.items()})))
            return 0
        dump = json.loads(Path(a.dump).read_text())
        thr = parse_set(a.set)
        verdict, reasons, m = judge(dump, thr)
    except SystemExit:
        raise
    except Exception as ex:  # noqa: BLE001
        print(f"preroute_gate: error {ex}")
        return 2
    rep = dict(verdict=verdict, reasons=reasons, thresholds=dict(THRESHOLDS, **thr), classes=m,
               period_ps=dump.get("period_ps"), truncated=dump.get("truncated"), dump_ms=a.dump_ms,
               find_ms=dump.get("find_ms"), classify_ms=dump.get("classify_ms"))
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1))
    print(f"preroute_gate: {verdict}: {summary_line(m)}")
    if verdict == "FAIL":
        print("PREROUTE_MARGIN: " + " | ".join(reasons))
        return 0 if a.warn_only else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
