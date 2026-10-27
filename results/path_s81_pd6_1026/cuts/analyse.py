#!/usr/bin/env python3
"""PATH-S81-PD6 cut evidence step 3 (verdict): per G0 cut line, per gcell on the line inside the partition segment,
measured routed usage = d_all / cap_eff on the layers whose wires cross the cut (horizontal cut -> M5/M7 vertical;
vertical cut -> M4/M6 horizontal); M8/M9 = INFO (clock + leftover, adj 0.4 not reflected in dbGCellGrid).
  cap, use  = GRT dbGCellGrid after the PD5 combo global_route rerun unchanged (probe; per-layer demand identical to the
              PD5 log), use = adjustment-reserved + OBS-blocked + routed;
  use0      = the same dbGCellGrid after an EMPTY route (probe0: every net special) = adjustment + OBS reservation only;
  cap_eff   = cap - use0 = the tracks GRT could route there (0 = fully reserved/blocked); d_all = use - use0 = routed;
  d_cross   = nets whose guide box (route_<C>.guide of the PD5 run) on that layer spans the line = wires crossing it.
  ratio     = d_all / cap_eff over gcells with cap_eff > 0.  Verdict WAIVE if max ratio <= 0.9 else LIST.
Cross-check: sum d_cross along the segment vs the G0 bit count of that segment (static model)."""
import json
import sys
from collections import defaultdict

corner = sys.argv[1] if len(sys.argv) > 1 else "TT"
cuts = json.load(open("cuts_composed.json"))
S = json.load(open(f"strip_demand_{corner}.json"))
U0 = {}
for ln in open(f"probe0_{corner}/gcells0_{corner}.txt"):      # empty-route probe: usage = adjustment + OBS reservation
    o, at, L, xi, yi, x0, y0, cap, use = ln.split()
    U0[(o, float(at), L, int(xi), int(yi))] = (float(cap), float(use))
by = defaultdict(list)
nchk = [0, 0, 0]
for r in S["gcells"]:
    cap0, use0 = U0[(r["orient"], r["at"], r["L"], r["xi"], r["yi"])]
    assert cap0 == r["cap"]
    r["cap_eff"] = cap0 - use0                      # GRT routable tracks (after adjustment + OBS)
    r["d_all_guides"] = r["d_all"]
    r["d_all"] = r["use"] - use0                    # GRT routed usage in the gcell (exact, from the two probes)
    nchk[0] += 1
    nchk[1] += r["d_all"] == r["d_all_guides"]
    nchk[2] += abs(r["d_all"] - r["d_all_guides"]) <= 2
    by[(r["orient"], r["at"])].append(r)
print("gcells", nchk[0], "routed==guide count", nchk[1], "within 2", nchk[2])
res = []
for c in cuts:
    o, at = c["orient"], c["at_um"]
    cross = ("M5", "M7") if o == "horizontal" else ("M4", "M6")
    lo, hi = c["seg_lo_um"] * 1000, c["seg_hi_um"] * 1000
    G = 10800
    # gcells inside the segment along the line (segment = partition extent along the cut)
    rows = [r for r in by[(o, at)] if lo - G < ((r["xi"] if o == "horizontal" else r["yi"]) * G) < hi]
    # the line row/col: the gcell index containing the cut (at*1000 // G); keep the neighbour if on a boundary
    ci = int(round(at * 1000)) // G
    line = [r for r in rows if (r["yi"] if o == "horizontal" else r["xi"]) == ci]
    per = {}
    for L in cross + (("M9",) if o == "horizontal" else ("M8",)):
        R = [r for r in line if r["L"] == L]
        live = [r for r in R if r["cap_eff"] > 0]
        mx = max(live, key=lambda r: r["d_all"] / r["cap_eff"]) if live else None
        per[L] = dict(gcells=len(R), gcells_routable=len(live),
                      max_ratio=round(mx["d_all"] / mx["cap_eff"], 4) if mx else None,
                      max_at=dict(gcell_ll_um=[mx["xi"] * G / 1000, mx["yi"] * G / 1000], d=mx["d_all"],
                                  cap_eff=mx["cap_eff"]) if mx else None,
                      mean_ratio=round(sum(r["d_all"] for r in live) / sum(r["cap_eff"] for r in live), 4) if live else None,
                      full_gcells=sum(1 for r in live if r["d_all"] >= r["cap_eff"]),
                      max_cross_ratio=round(max(r["d_cross"] / r["cap_eff"] for r in live), 4) if live else None,
                      d_cross_sum=sum(r["d_cross"] for r in R), cap_eff_sum=sum(r["cap_eff"] for r in R))
    sig = [per[L] for L in cross if per[L]["max_ratio"] is not None]
    worstL = max(cross, key=lambda L: per[L]["max_ratio"] or 0)
    mx = per[worstL]["max_ratio"]
    mxc = max(per[L]["max_cross_ratio"] or 0 for L in cross)
    allc = [r for r in line if r["L"] in cross and r["cap_eff"] > 0]
    res.append(dict(cut=f"{o[0]}{at:g}:{c['part']}", orient=o, at_um=at, part=c["part"],
                    seg_um=[c["seg_lo_um"], c["seg_hi_um"]], g0_ratio=c["g0_ratio"], g0_bits=c["bits"],
                    g0_tracks=c["g0_tracks"], crossing_layers=cross, line_gcell_index=ci, per_layer=per,
                    max_ratio=mx, max_cross_ratio=mxc, max_layer=worstL, max_at=per[worstL]["max_at"],
                    mean_ratio=round(sum(r["d_all"] for r in allc) / sum(r["cap_eff"] for r in allc), 4) if allc else None,
                    crossing_nets=sum(per[L]["d_cross_sum"] for L in cross),
                    routable_tracks=sum(per[L]["cap_eff_sum"] for L in cross),
                    verdict="WAIVE" if mx is not None and mx <= 0.9 else "LIST"))
json.dump(dict(method=__doc__, corner=corner, guide_gcell_sum=S["guide_gcell_sum"], cuts=res),
          open(f"cut_evidence_{corner}.json", "w"), indent=1)
with open(f"cut_evidence_{corner}.txt", "w") as f:
    f.write(f"PATH-S81-PD6 cut evidence, PD5 combo GRT {corner} (method: cut_evidence_{corner}.json 'method')\n")
    f.write("%-17s %5s %6s %6s %-4s %-20s %6s %5s %6s %7s %7s %s\n" % (
        "cut", "G0", "max", "maxX", "lay", "gcell_ll_um d/cap", "mean", "full", "G0bit", "x_nets", "tracks", "verdict"))
    for r in res:
        a = r["max_at"]
        f.write("%-17s %5.2f %6.3f %6.3f %-4s %-20s %6.3f %5d %6d %7d %7d %s\n" % (
            r["cut"], r["g0_ratio"], r["max_ratio"], r["max_cross_ratio"], r["max_layer"],
            "%g,%g %d/%g" % (a["gcell_ll_um"][0], a["gcell_ll_um"][1], a["d"], a["cap_eff"]),
            r["mean_ratio"], sum(r["per_layer"][L]["full_gcells"] for L in r["crossing_layers"]), r["g0_bits"],
            r["crossing_nets"], r["routable_tracks"], r["verdict"]))
print(open(f"cut_evidence_{corner}.txt").read())
