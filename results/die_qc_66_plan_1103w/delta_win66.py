#!/usr/bin/env python3
"""DIE-QC-66/PLAN QC clock plan event (11-03, re-apply of the DIE-QC-65/CLK recipe on the y-shrunk die 25643.52):
per-type block arrival-contract windows re-derived on the measured die clock of the v3 clock kit (v2 form: region DME early-merge + snake on the early su_lane core-tap regions
sl_{E,W}{0..5}_su_l{0,1} and merge on every sl_{E,W}{0..5}_su_c, on post-RED plan_qc52), whole-die combo GRT50 TT/FF.

Metadata only (DIE-QC-56 recipe, OWNER 12.28b): for every type whose measured nominal 12.25 kit-contract need
(--nominal-arrival single, worst region of the type) exceeds its clock.tap_window.per_type_ps W_t, set
W_t = ceil10(need + 10), cap T/4.  Windows are only raised (types within their window keep W_t).  No RTL, cell,
placement, cycle or tap change.

usage: delta_clk_win_1103.py NEED_JSON PLAN_IN PLAN_OUT [--report OUT.tsv]
NEED_JSON = {region: [need_ps, launch_tap, capture_tap]} (die_sta_related intra kit-contract damage per region).
"""
import argparse, json, math

TAG = "DIE-QC-66/PLAN-1103"


def derive(P, need):
    parts = {p["name"]: p["type"] for p in P["partitions"]}
    tw = P["clock"]["tap_window"]
    pt = tw["per_type_ps"]; w0 = float(tw["window_ps"]); cap = float(P["die"]["period_ps"]) / 4
    worst = {}
    for r, v in need.items():
        t = parts.get(r)
        if t is not None and (t not in worst or v[0] > worst[t][0]):
            worst[t] = (float(v[0]), r, v[1], v[2])
    rows, changes = [], {}
    for t in sorted(worst):
        n, r, a, b = worst[t]
        w = float(pt.get(t, w0))
        nw = w
        if n > w:
            nw = float(min(cap, math.ceil((n + 10.0) / 10.0) * 10))
            assert nw >= n, (t, n, nw, "need over cap T/4")
            changes[t] = (w, nw)
        rows.append((t, w, round(n, 2), nw, r, a, b))
    return rows, changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("need"); ap.add_argument("plan_in"); ap.add_argument("plan_out")
    ap.add_argument("--report")
    a = ap.parse_args()
    text = open(a.plan_in).read()
    P = json.loads(text)
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    rows, ch = derive(P, json.load(open(a.need)))
    tw = P["clock"]["tap_window"]
    for t, (w, nw) in ch.items():
        tw["per_type_ps"][t] = int(nw) if float(nw).is_integer() else nw
    if ch:
        tw["note"] += (f" | {TAG} (QC clock plan event, metadata only, DIE-QC-56 recipe): {len(ch)} types raised to "
                       f"ceil10(need+10) on the v3 die clock kit of the y-shrunk die (shrink2 2fd11f0f94 + CA re-fix eafccfed43, "
                       f"region DME early-merge on sl_*_su_l0/l1 + merge on all sl_*_su_c, combo GRT50 TT/FF, main die_sta_related nominal single arrival): "
                       + ", ".join(f"{t} {w:g}->{nw:g}" for t, (w, nw) in sorted(ch.items())))
    open(a.plan_out, "w").write(json.dumps(P, separators=seps) + "\n")
    if a.report:
        with open(a.report, "w") as f:
            f.write("type\tW_old\tneed_ps\tW_new\tworst_region\tlaunch\tcapture\n")
            for r in rows:
                f.write("\t".join(str(x) for x in r) + "\n")
    print(f"{len(ch)} types changed:", {t: v for t, v in sorted(ch.items())})


if __name__ == "__main__":
    main()
