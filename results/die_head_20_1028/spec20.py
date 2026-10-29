#!/usr/bin/env python3
"""DIE-HEAD-20: ca_ring_latency/1 spec of hd_tile from meas20.tcl outputs (TT/FF .ck + fwd_*.txt).
writer = u_cland_i ring write side (s_d, s_lap, s_w, tc, g_tag; DH18: 2298), reader = read side (dch, oh, rp, glo, ghi,
r_*; DH18: 628).  fclk_in/reader = [min early, max late] over their CK pins; fwd_out = fclk_out_o driver output."""
import json, re, sys
from pathlib import Path
d = Path(sys.argv[1]); src = sys.argv[2]
W = re.compile(r"^u_cland_i/(u_ring\.)?(s_d|s_lap|s_w|tc|g_tag)\b"); R = re.compile(r"^u_cland_i/(u_ring\.)?(dch|oh|rp|glo|ghi|r_)")
spec = {"schema": "ca_ring_latency/1", "source": src, "types": {"hd_tile": {}}, "fwd_wire_ps": {"TT": [0.0, 1.0], "FF": [0.0, 1.0]}}
for c in ("TT", "FF"):
    w, r, noarr = [], [], 0
    for l in (d / f"{c}.ck").read_text().splitlines():
        f = l.split()
        if f[0] == "NOARR": noarr += 1; continue
        a, e = float(f[2]), float(f[3])
        if W.match(f[1]): w.append((e, a))
        elif R.match(f[1]): r.append((e, a))
    ch = [l.split() for l in (d / f"fwd_{c}.txt").read_text().splitlines() if l.startswith("CHAIN 0 ")][0]
    fo = [float(ch[ch.index("out_min") + 1]), float(ch[ch.index("out_max") + 1])]
    rng = lambda v: [round(min(x[0] for x in v), 1), round(max(x[1] for x in v), 1)]
    spec["types"]["hd_tile"][c] = {"fwd_out_ps": [round(x, 1) for x in fo], "fclk_in_ps": rng(w), "reader_ps": rng(r)}
    print(c, "writers", len(w), "readers", len(r), "noarr", noarr, "fwd driver", ch[2], ch[3], spec["types"]["hd_tile"][c])
json.dump(spec, open(sys.argv[3], "w"), indent=1)
