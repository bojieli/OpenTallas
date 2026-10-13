#!/usr/bin/env python3
"""dsfd_engram_c CTS-stop gate record (el1013-s81-engram 2026-10-13).

    gate_report.py CKP.out PAIR.out --vclk PS --label L --commit C --out gate.json

CKP.out / PAIR.out = gate_sta.sh ckpath / pairs on a CTS-stop run of the composition (cts_stop.sh).  Per child: top
tree arrival at the entry chain, chain stage delays, clock-pin arrival + slew, the view's internal insertion
(max_clock_tree_path of the installed liberty, same corner) and leaf = pin arrival + insertion.  PASS = leaf spread
<= 80 ps at TT and at FF, every child clock-pin slew <= 120 ps.  The pair table (worst setup at TT under the route SDC,
worst hold at FF) is recorded as measured; it is pre-route (placement parasitics)."""
import argparse, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/hier_contract"))
import child_lint  # noqa: E402
VIEW = {"win": "physical/s81_engc_tiles/views/ot_engc_t_win/ot_engc_t_win", "io": "physical/s81_engc_tiles/views/ot_engc_t_io/ot_engc_t_io",
        "ws": "physical/s81_engc_tiles/views/ot_engc_t_ws/ot_engc_t_ws", "pb1": "physical/s81_engc_tiles/views/ot_engc_t_pbb/ot_engc_t_pbb",
        "pb0": "physical/s81_engc_tiles/views/ot_engc_t_pbc/ot_engc_t_pbc", "pb2": "physical/s81_engc_tiles/views/ot_engc_t_pbc/ot_engc_t_pbc",
        "lkp": "physical/s81_ph_views/closed/dsfd_engram_lkp/dsfd_engram_lkp", "sink": "physical/s81_ph_views/closed/dsfd_engram_sink/dsfd_engram_sink"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ckp"); ap.add_argument("pairs"); ap.add_argument("--vclk", type=int, required=True)
    ap.add_argument("--label", required=True); ap.add_argument("--commit", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ins = {c: {k: child_lint.clock_insertion((ROOT / f"{v}_{c.lower()}.lib").read_text())["ck"] for k, v in VIEW.items()} for c in ("TT", "FF")}
    d = {}
    for l in open(a.ckp):
        f = l.split()
        if len(f) < 4 or f[0] != "CKP":
            continue
        if f[2] == "MAC":
            d.setdefault(f[1], {}).setdefault(f[3][2:], {}).update(pin_arrival_ps=float(f[5]), pin_slew_ps=float(f[7]))
        else:
            ch = re.search(r"u_hdly_ck_(\w+?)\.", f[3]).group(1)
            d.setdefault(f[1], {}).setdefault(ch, {}).setdefault("st", []).append((float(f[5]), float(f[9])))
    rec = {"schema": "opentallas.s81.engram-c-cts-gate.v1", "label": a.label, "commit": a.commit, "vclk_ps": a.vclk, "corners": {}}
    ok = True
    for c in ("TT", "FF"):
        rows = {}
        for ch, e in sorted(d[c].items()):
            st = sorted(e.pop("st", []))
            e["tree_arrival_ps"] = st[0][0] if st else e["pin_arrival_ps"]
            e["entry_stage_delays_ps"] = [s[1] for s in st]
            e["insertion_max_ps"] = round(ins[c][ch]["max_ps"], 1); e["insertion_min_ps"] = round(ins[c][ch]["min_ps"], 1)
            e["leaf_ps"] = round(e["pin_arrival_ps"] + ins[c][ch]["max_ps"], 1)
            rows[ch] = e
        leaf = [r["leaf_ps"] for r in rows.values()]
        sp = round(max(leaf) - min(leaf), 1); sl = max(r["pin_slew_ps"] for r in rows.values())
        rec["corners"][c] = {"children": rows, "leaf_spread_ps": sp, "leaf_latest_ps": max(leaf), "max_pin_slew_ps": sl,
                             "pin_arrival_spread_ps": round(max(r["pin_arrival_ps"] for r in rows.values()) - min(r["pin_arrival_ps"] for r in rows.values()), 1)}
        ok &= sp <= 80.0 and sl <= 120.0
    pairs = {"setup_TT_route_sdc": {}, "hold_FF": {}}
    for l in open(a.pairs):
        f = l.split()
        if f[:1] != ["PAIR"]:
            continue
        k = "setup_TT_route_sdc" if f[2] == "max" else "hold_FF"
        pairs[k]["WNS" if f[3] == "WNS" else f"{f[3]}->{f[4]}"] = float(f[-1])
    rec["pairs_pre_route_ps"] = pairs
    rec["verdict"] = "PASS" if ok else "FAIL"
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print("ENGC_CTS_GATE", rec["verdict"], "leaf spread TT", rec["corners"]["TT"]["leaf_spread_ps"], "FF", rec["corners"]["FF"]["leaf_spread_ps"],
          "max slew", max(rec["corners"][c]["max_pin_slew_ps"] for c in ("TT", "FF")), "setup WNS (route SDC)", pairs["setup_TT_route_sdc"].get("WNS"),
          "hold WNS FF", pairs["hold_FF"].get("WNS"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
