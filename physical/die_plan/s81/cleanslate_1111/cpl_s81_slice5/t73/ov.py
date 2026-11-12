#!/usr/bin/env python3
"""CPL-S81-SLICE-5: put every vn<->lane hi/ho station reg on its quad site (S81-LEAF-CYC quad form); same reg counts
(a 2-reg plan entry keeps 2 regs: the first on the street halfway from the vn pin, the second on the quad site).
usage: ov.py BASE_PLAN COMPANION_IN QUAD_SITES COMPANION_OUT"""
import json, re, sys
T = "ot_s81sl_leaf__t73"
base, cin, sf, cout = sys.argv[1:5]
B = json.load(open(base))["partition_types"][T]["internal_stations"]
C = json.load(open(cin)); S = {int(k): v for k, v in json.load(open(sf)).items()}
RX = re.compile(r"^core:u_lf\.u_vn\.u_[ab]\.(hq_|hr_|hw_)\w+\|(?:core:)?u_lf\.u_vp\.g_ln\[(\d+)\]\.u_l$")
st = C[T]["internal_stations"]; assert len(st) == len(B)
n = 0
for b, e in zip(B, st):
    m = RX.match(b["conn"])
    if not m: continue
    s = S[int(m.group(2))]; k = len(e["regs_um"])
    if k == 1: e["regs_um"] = [list(s)]
    else:
        f = e["from_um"]; e["regs_um"] = [[s[0], round(round(((f[1] + s[1]) / 2) / 0.27) * 0.27, 3)]] * (k - 1) + [list(s)]
        e["regs_um"] = [list(r) for r in e["regs_um"]]
    n += 1
json.dump(C, open(cout, "w"))
print("hi/ho entries on quad sites:", n)
