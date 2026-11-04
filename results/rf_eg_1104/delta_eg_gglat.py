#!/usr/bin/env python3
"""S81 RF-EG (DIE-S81-54/EG 11-04): u_c.u_eg.u_gg origin onto the 8.64-um lattice in all 16 C types (+4.32 um x inside the
same RF-EG box, 267.84 wide: egg now flush with the box E edge).  Clock tap and reset pin/site move with the block; clk pin
stays over the 8.64-um channel between u_nh and u_nk, rst_n reaches it through the 8.64-um row channel below egg.
Text-level edit; output JSON equals the dict delta.    python3 delta_eg_gglat.py <plan in> <plan out>"""
import json, re, sys
src, out = sys.argv[1:]
txt = open(src).read(); plan = json.loads(txt)
DX = 4.32; R = lambda v: round(v + DX, 3)
n = 0
for name, t in plan["partition_types"].items():
    hc = [c for c in t.get("hard_cores") or [] if c["inst"] == "u_c.u_eg.u_gg"]
    if not hc: continue
    n += 1; hc[0]["origin_um"][0] = R(hc[0]["origin_um"][0])
    assert abs(hc[0]["origin_um"][0] / 8.64 - round(hc[0]["origin_um"][0] / 8.64)) < 1e-6, name
    tp = next(x for x in t["clock"]["taps"] if x["name"] == "u_c.u_eg.u_gg.clk"); tp["xy"][0] = R(tp["xy"][0])
    rs = next(x for x in t["clock"]["landing_contract"]["collector_tree"]["core_resets"] if x["inst"] == "u_c.u_eg.u_gg")
    rs["pin_um"][0] = R(rs["pin_um"][0]); rs["xy"][0] = R(rs["xy"][0])
assert n == 16, n
num = r"(-?[0-9.]+)"
new, a = re.subn(r'(\{"inst":"u_c\.u_eg\.u_gg","module":"ot_s81sl_egg"[^{}]*?"origin_um":\[)' + num, lambda m: m.group(1) + str(R(float(m.group(2)))), txt)
new, b = re.subn(r'(\{"name":"u_c\.u_eg\.u_gg\.clk","kind":"core","xy":\[)' + num, lambda m: m.group(1) + str(R(float(m.group(2)))), new)
new, c = re.subn(r'(\{"inst":"u_c\.u_eg\.u_gg","pin":"rst_n","pin_um":\[)' + num + r'(,[0-9.]+\],"xy":\[)' + num,
                 lambda m: m.group(1) + str(R(float(m.group(2)))) + m.group(3) + str(R(float(m.group(4)))), new)
assert (a, b, c) == (16, 16, 16), (a, b, c)
assert json.loads(new) == plan, "text edit differs from dict delta"
open(out, "w").write(new); print("delta_eg_gglat OK", n)
