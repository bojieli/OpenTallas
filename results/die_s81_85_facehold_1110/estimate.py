#!/usr/bin/env python3
"""FACEHOLD-S81 out-face latch estimate on the measured routed DBs (analytic, GRT-free; [inferred]).
Form: last station u_ft_<o>_<n-1> -> ot_dp_lk (DLLx1, transparent low, on the station's tap) FIRM at the out face -> port.
  FF hold at the out port (out_min 0):  new_arrival = Lc + T/2 + ckq_lat_min + wire_after ; old = Lc + ckq_ff + wire
      -> delta >= T/2 + ckq_lat_min - (old_arrival - Lc)            (conservative: wire_after counted as saved)
  FF hold station -> latch (same tap, latch beside the station): ckq_ff_min + wire_before - hold_lat - unc - skew
      -> wire_before 0, skew 0 (same leaf) and skew 15 ps (different leaf of the tap, t24 g2->g3 measured 10.7)
  TT setup at the out port (out_max):  delta = -(T/2 + ckq_lat_max) + ckq_ff + wire_before  -> conservative -(T/2 + ckq_lat_max)
DLLx1_ASAP7_75t_R arcs from FTLOCK-S81 estimate.py (RVT SEQ liberty, 20 ps slew / 1.44 fF).
usage: estimate.py ROWDIR ...   (ROWDIR/{census_ff.tsv, worst_to_out_ff.rpt, census_tt.tsv})"""
import json
import re
import sys
from pathlib import Path

T = 833.0
DLL = {"FF": dict(ckq_min=27.48, hold=-1.45), "TT": dict(ckq_max=50.42, setup=15.41)}
HOLD_UNC = 25.0


def paths(txt):
    out = []
    for blk in re.split(r"(?=^Startpoint: )", txt, flags=re.M):
        if not blk.startswith("Startpoint:"):
            continue
        sl = re.search(r"^\s*(-?[\d.]+)\s+slack", blk, re.M)
        ck = [l for l in blk.splitlines() if "/CLK (" in l]
        q = [l for l in blk.splitlines() if re.search(r"/QN? \(", l)]
        arr = re.search(r"^\s*(-?[\d.]+)\s+data arrival time", blk, re.M)
        if not (sl and ck and q and arr):
            continue
        lc = float(re.findall(r"-?\d+\.\d+", ck[0])[1])
        qt = float(re.findall(r"-?\d+\.\d+", q[0])[1])
        out.append(dict(start=re.match(r"Startpoint: (\S+)", blk).group(1), end=re.search(r"Endpoint: (\S+)", blk).group(1),
                        slack=float(sl.group(1)), lc=lc, ckq=round(qt - lc, 2), arrival=float(arr.group(1)),
                        lc_to_port=round(float(arr.group(1)) - lc, 2)))
    return out


def row(d):
    d = Path(d)
    cen = [l.rstrip("\n").split("\t") for l in open(d / "census_ff.tsv")][1:]
    oface = {}
    for r in cen:
        if r[6] == "port":
            oface[r[5]] = min(float(r[1]), oface.get(r[5], 1e9))
    rep = paths((d / "worst_to_out_ff.rpt").read_text()) if (d / "worst_to_out_ff.rpt").is_file() else []
    span = max((p["lc_to_port"] for p in rep), default=None)
    ckq = min((p["ckq"] for p in rep), default=None)
    res = dict(row=d.name, out_face_violators=len(oface), out_face_wns=min(oface.values()) if oface else None)
    if oface:
        res["ff_out_hold_worst_paths"] = [dict(p, new_slack_est=round(p["slack"] + T / 2 + DLL["FF"]["ckq_min"] - p["lc_to_port"], 2))
                                          for p in rep]
        res["ff_out_hold_new_wns_bound"] = round(min(oface.values()) + T / 2 + DLL["FF"]["ckq_min"] - span, 2)
        res["ff_out_hold_bound_note"] = f"worst old slack + T/2 + DLL ckq_min - max measured Lc->port span {span}"
    if ckq is not None:
        res["ff_station_to_latch_hold_est"] = {f"skew_{s}": round(ckq - DLL["FF"]["hold"] - HOLD_UNC - s, 2) for s in (0, 15)}
        res["ff_station_ckq_min_measured"] = ckq
    tt = d / "census_tt.tsv"
    if tt.is_file():
        rows = [l.rstrip("\n").split("\t") for l in open(tt)][1:]
        ft = {}
        for s, a, e in rows:
            bus = re.sub(r"\[\d+\]$", "", e)
            if not bus.startswith("ft"):
                continue
            ft[bus] = min(float(s), ft.get(bus, 1e9))
        cost = T / 2 + DLL["TT"]["ckq_max"]
        res["tt_out_setup_now"] = dict(sorted(ft.items()))
        res["tt_out_setup_with_latch_bound"] = {b: round(v - cost, 2) for b, v in sorted(ft.items())}
        res["tt_cost_bound_ps"] = cost
    return res


def tt2(rpt):
    """TT max per output port (report_checks -format full): new slack with the face latch =
    required - (Lc + T/2 + DLL ckq_max + every non-HB stage after the station Q).  HB* hold pads on the out face are
    dropped (the latch makes out_min 0 hold-safe, so the in-type hold repair has nothing to pad there); the station's
    own INV and the port buffer stay after the latch (conservative)."""
    res = {}
    for blk in re.split(r"(?=^Startpoint: )", Path(rpt).read_text(), flags=re.M):
        if not blk.startswith("Startpoint:"):
            continue
        end = re.search(r"Endpoint: (\S+)", blk).group(1)
        bus = re.sub(r"\[\d+\]$", "", end)
        if not bus.startswith("ft"):
            continue
        lines = blk.splitlines()
        lc = None
        stages = []
        seen_q = False
        for l in lines:
            if "clock network delay" in l and lc is None:
                lc = float(re.findall(r"-?\d+\.\d+", l)[1])
            m = re.match(r"\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+[\^v]\s+(\S+)\s+\((\S+)\)", l)
            if not m:
                continue
            if re.search(r"/QN?$", m.group(3)):
                seen_q = True
                continue
            if seen_q:
                stages.append((float(m.group(1)), m.group(4)))
        req = re.search(r"^\s*(-?[\d.]+)\s+data required time", blk, re.M)
        sl = re.search(r"^\s*(-?[\d.]+)\s+slack", blk, re.M)
        if lc is None or not req or not sl:
            continue
        after = sum(d for d, c in stages if not c.startswith("HB"))
        new = float(req.group(1)) - (lc + T / 2 + DLL["TT"]["ckq_max"] + after)
        vck = [float(re.findall(r"-?\d+\.\d+", l)[1]) for l in lines if "clock network delay (ideal)" in l]
        r = res.setdefault(bus, dict(n=0, now_wns=1e9, latch_wns=1e9, latch_port_arrival_vs_vclk_max=-1e9))
        if vck:     # the receiver sees this port at (arrival - its vclk): compare with the receiver's in_max contract
            r["latch_port_arrival_vs_vclk_max"] = round(max(r["latch_port_arrival_vs_vclk_max"],
                                                            lc + T / 2 + DLL["TT"]["ckq_max"] + after - (vck[-1] - T)), 2)
        r["n"] += 1
        r["now_wns"] = min(r["now_wns"], float(sl.group(1)))
        if new < r["latch_wns"]:
            r.update(latch_wns=round(new, 2), worst_end=end, worst_lc=lc, worst_after=round(after, 2))
    return res


if __name__ == "__main__":
    if sys.argv[1] == "tt2":
        print(json.dumps(tt2(sys.argv[2]), indent=1))
        sys.exit(0)
    out = [row(d) for d in sys.argv[1:]]
    print(json.dumps(out, indent=1))
