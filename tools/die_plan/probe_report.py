"""probe_report: PROBE.json of a full-depth probe kit (OT_PROBE_THROUGH=1, PROBE-THROUGH-1122, COORD 18:5x).

A probe kit runs past the triage stops of a normal kit (post-place PLACE-SETUP-STOP, the post-CTS / post-GRT SETUP_TRIAGE and insertion
band gates, the FF structural hold gate, the GRT policy gate, the hop census) in estimate mode, with GRT congestion allowed, so one build
names every failing class at once instead of one per build.  Each stop it passed is a line in K/PROBE_STOPS.log.  This script reads what
the kit left and writes K/PROBE.json:

  stops_passed      the stop lines the probe ran through (what a normal kit would have ended on, in order)
  setup             post-place WNS + worst path (place_setup_stop.json), pre-route estimate (postcts_gate_TT.json), routed TT (signoff)
  setup_classes     violated paths of the deepest TT timing report grouped by (start block, end block): count, worst slack
  clock_insertion   pin-register insertion mean / min / max vs the bound and tolerance (postcts_gate_<C>.json, band verdict)
  hold              FF hold estimate (postcts_gate_FF.json) and the FF structural hold gate lines (hold_gate.log)
  congestion        GRT overflow per layer / total (5_1_grt.log) and the congestion report markers (count + worst boxes)
  drv               slew / cap / fanout violation counts (newest ORFS log or signoff record)

A probe kit is never a sign-off: signoff.py adds the reason 'probe_through' for any kit with K/probe_through.on, and PROBE.json says
signoff=false.  Usage: probe_report.py KIT [--goal G] [--rc N]  (exit 0; a missing input is recorded as null, never an error)."""
import argparse
import glob
import json
import os
import re
import sys
import time

SCHEMA = "opentallas.probe/1"
SLACK_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s+slack \((VIOLATED|MET)\)", re.M)


def _read(p):
    try:
        with open(p, errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _json(p):
    try:
        with open(p) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _newest(pats):
    got = [p for pat in pats for p in glob.glob(pat)]
    return max(got, key=os.path.getmtime) if got else None


def block(pin):
    """the top-level block of a pin / instance path (u_bound.u_x.q -> u_x under a u_bound wrapper; a port -> 'port')"""
    parts = [x for x in re.split(r"[./]", pin or "") if x]
    if len(parts) <= 1:
        return "port"
    if parts[0] in ("u_bound", "u_top") and len(parts) > 2:
        parts = parts[1:]
    return re.sub(r"\[\d+\]", "[*]", parts[0])


def path_classes(text, limit=20):
    """OpenSTA report_checks text -> [{start_block, end_block, count, worst_ps}] of the VIOLATED paths, worst first"""
    cls = {}
    for blk in re.split(r"(?m)^Startpoint: ", text)[1:]:
        st = blk.split()[0] if blk.split() else ""
        m = re.search(r"(?m)^Endpoint: (\S+)", blk)
        s = SLACK_RE.search(blk)
        if not m or not s or s.group(2) != "VIOLATED":
            continue
        k = (block(st), block(m.group(1)))
        c = cls.setdefault(k, {"start_block": k[0], "end_block": k[1], "count": 0, "worst_ps": 0.0, "example": f"{st} -> {m.group(1)}"})
        c["count"] += 1
        c["worst_ps"] = min(c["worst_ps"], float(s.group(1)))
    return sorted(cls.values(), key=lambda c: c["worst_ps"])[:limit]


def congestion(grt_log, rpt):
    out = {"log": grt_log, "layers": {}, "total_overflow": None, "report": rpt, "markers": None, "worst_boxes": []}
    t = _read(grt_log) if grt_log else ""
    for ln in t.splitlines():
        m = re.match(r"^\s*([A-Za-z]+\d+|Total)\s+(\d+)\s+(\d+)\s+(-?[\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*$", ln)
        if m:
            ov = int(m.group(7))
            if m.group(1) == "Total":
                out["total_overflow"] = ov
            elif ov:
                out["layers"][m.group(1)] = ov
    if rpt:
        r = _read(rpt)
        boxes = re.findall(r"bbox\s*=\s*\(\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\)\s*-\s*\(\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\)", r)
        out["markers"] = len(boxes)
        out["worst_boxes"] = [[float(x) for x in b] for b in boxes[:10]]
    return out


def drv(texts):
    out = {}
    for t in texts:
        for kind, pat in (("slew", r"max slew violations?:?\s+(\d+)|Found (\d+) slew violations"),
                          ("cap", r"max cap(?:acitance)? violations?:?\s+(\d+)|Found (\d+) cap(?:acitance)? violations"),
                          ("fanout", r"max fanout violations?:?\s+(\d+)|Found (\d+) fanout violations")):
            hits = [int(a or b) for a, b in re.findall(pat, t, re.I)]
            if hits:
                out[kind] = hits[-1]
    return out


def build(K, goal=None, rc=None):
    base = os.path.join(K, "run", "results", "asap7", "*", "base")
    logs = os.path.join(K, "run", "logs", "asap7", "*", "base")
    reps = os.path.join(K, "run", "reports", "asap7", "*", "base")
    stops = [x.strip() for x in _read(os.path.join(K, "PROBE_STOPS.log")).splitlines() if x.strip()]
    pp = _json(os.path.join(K, "place_setup_stop.json"))
    gate = {c: _json(os.path.join(K, f"postcts_gate_{c}.json")) for c in ("TT", "FF")}
    so = None
    for f in sorted(glob.glob(os.path.join(K, "signoff*", "signoff.json")), key=os.path.getmtime):
        so = f
    rec = _json(so) if so else None
    tt_rep = _newest([os.path.join(K, "signoff*", "tt", "sta.log")]) or os.path.join(K, "postplace_setup.log")
    grt_log = _newest([os.path.join(logs, "5_1_grt.log")])
    ck = {}
    for c, g in gate.items():
        if g:
            ck[c] = {k: g.get(k) for k in ("pinreg_n", "pinreg_mean_ps", "pinreg_min_ps", "pinreg_max_ps", "bound_ps", "dev_ps", "tol_ps",
                                          "band_verdict", "verdict")}
    hold_lines = [ln.strip() for ln in _read(os.path.join(K, "hold_gate.log")).splitlines() if "OT_HOLD_GATE" in ln][-12:]
    st = (((rec or {}).get("checks") or {}).get("setup_tt") or {})
    tt = (((rec or {}).get("corners") or {}).get("tt") or {})
    out = {
        "schema": SCHEMA, "kit": K, "made": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "goal": goal, "rc": rc,
        "signoff": False, "note": "full-depth probe (OT_PROBE_THROUGH=1): estimate mode past triage stops, never a sign-off",
        "deepest": next((s for s, pat in (("route", "5_route.odb"), ("grt", "5_1_grt.odb"), ("cts", "4_cts.odb"), ("place", "3_place.odb"))
                         if glob.glob(os.path.join(base, pat))), None),
        "stops_passed": stops,
        "setup": {"post_place": pp, "pre_route_est_ps": (gate.get("TT") or {}).get("setup_wns_est_ps"),
                  "routed_tt": ({k: st.get(k) for k in ("verdict", "wns_ps", "tns_ps", "violators")} if st else None),
                  "routed_tt_ocv5_wns_ps": tt.get("ocv5_wns_max"), "signoff_record": so,
                  "report": tt_rep if os.path.exists(tt_rep) else None},
        "setup_classes": path_classes(_read(tt_rep)) if os.path.exists(tt_rep) else [],
        "clock_insertion": ck,
        "hold": {"ff_est_ps": (gate.get("FF") or {}).get("hold_wns_est_ps"), "hold_gate": hold_lines},
        "congestion": congestion(grt_log, _newest([os.path.join(reps, "congestion.rpt"), os.path.join(reps, "*congestion*.rpt")])),
        "drv": ({"slew": tt.get("slew_viol"), "cap": tt.get("cap_viol"), "fanout": tt.get("fanout_viol"), "source": "signoff tt"} if tt else
                drv([_read(p) for p in sorted(glob.glob(os.path.join(logs, "*.log")), key=os.path.getmtime)[-3:]])),
    }
    classes = []
    if stops:
        classes += sorted({re.sub(r"\s.*", "", re.sub(r"^FAIL_\w+\s+", "", s)) for s in stops})
    if out["setup_classes"] or (st and st.get("verdict") == "FAIL"):
        classes.append("setup")
    if out["congestion"]["total_overflow"]:
        classes.append("congestion")
    if any((v or {}).get("band_verdict") in ("ADVISORY", "FAIL") for v in ck.values()):
        classes.append("clock_insertion")
    if (out["hold"]["ff_est_ps"] or 0) < 0:
        classes.append("hold")
    if any(out["drv"].get(k) for k in ("slew", "cap", "fanout")):
        classes.append("drv")
    out["failing_classes"] = sorted(set(classes))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kit")
    ap.add_argument("--goal")
    ap.add_argument("--rc", type=int)
    a = ap.parse_args(argv)
    rec = build(os.path.abspath(a.kit), a.goal, a.rc)
    tmp = os.path.join(a.kit, ".PROBE.json.tmp")
    with open(tmp, "w") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(tmp, os.path.join(a.kit, "PROBE.json"))
    print(f"PROBE {a.kit}: deepest {rec['deepest']} failing {','.join(rec['failing_classes']) or 'none'} "
          f"({len(rec['stops_passed'])} stop(s) passed; not a sign-off)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
