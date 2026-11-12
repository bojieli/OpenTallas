#!/usr/bin/env python3
"""HEAD-94 11-12: per-port clock-arrival windows for the OPEN HEAD types from DIE-PROTO-1 kitwin_mean.json (measured kit needs on the FREG plan).
 usage: windows_event.py BASE_PLAN.json[.gz] OUT.json KITWIN_MEAN.json"""
import gzip, json, sys
from pathlib import Path
src = Path(sys.argv[1]); raw = gzip.open(src).read() if src.suffix == ".gz" else src.read_bytes()
P = json.loads(raw)
# (COORD 11-12, DIE-PROTO-1 die prototype) per-port clock-arrival windows re-derived from the measured kit needs (kitwin_mean.json,
# TT+FF, ceil 1 ps) on the FREG plan: per_port = max(current, need + 10) capped at the T/4 = 208 ps die cap, for OPEN types only.
# SIGNED/counted types (hd_ctl_n, hd_tile, hd_st_m, hd_st_n3_turn, hd_st_turn, hd_spn_wshim_rx, ...) are NOT widened (a widened window
# is a re-sign): their over-window ports are listed in the event for region-tree balance.  hd_lep0N keeps per_type_ps (need 224 > cap):
# region-tree balance, not a window.
K = json.load(open(sys.argv[3]))["per_port_ps"]
OPEN = ("hd_ctl", "hd_host_e", "hd_host_w", "hd_mesh", "hd_spn_end", "hd_st_n4")
TW = P["clock"]["tap_window"]; CAP = 208.0
rep = {}
for t in OPEN:
    need = K.get(t)
    if not need: continue
    cur = TW["per_port_ps"].setdefault(t, {})
    base = TW["per_type_ps"].get(t, TW.get("window_ps", 0))
    chg = 0
    for port, v in need.items():
        old = cur.get(port, base)
        new = min(CAP, max(old, float(v) + 10.0))
        if port not in cur or new != old:
            cur[port] = new; chg += 1
    TW["per_type_ps"][t] = max(float(TW["per_type_ps"].get(t, 0)), max(cur.values()))
    rep[t] = (chg, TW["per_type_ps"][t], max(need.values()))
over_signed = {}
for t, need in K.items():
    if t in OPEN: continue
    cur = TW["per_port_ps"].get(t) or {}
    base = TW["per_type_ps"].get(t, 0)
    n = [p for p, v in need.items() if v > cur.get(p, base)]
    if n: over_signed[t] = len(n)
print("windows widened (open types): type -> (ports set, per_type, max need)", rep)
print("over-window, NOT widened (signed or lep0N; tree balance):", over_signed)
TW["note"] = TW["note"] + " | HEAD-94 11-12: open types' per_port_ps re-derived from DIE-PROTO-1 kitwin_mean.json (FREG plan) as need+10 capped 208"

Path(sys.argv[2]).write_text(json.dumps(P, indent=1) + "\n")
