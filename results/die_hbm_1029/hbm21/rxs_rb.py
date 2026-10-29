#!/usr/bin/env python3
"""DIE-HBM-21: host_cp_rxs SRAM-edge rule (probe RB) into a plan dir core_macros.json (in place): 2 columns x 3 rows in
the S half, L column MY / R column R0 so every rd_out faces the 58.9-um centre channel (clock entry 216,216 inside);
the N face (1248 pins) gets a full-width logic field.  Probe RB: GRT 28377 -> 0 ov, channel_h 1.677 -> 0.407."""
import json, os, sys
f = sys.argv[1] + "/core_macros.json"; cm = json.load(open(f)); c = cm["cores"]["ot_hbm_host_cp_rxs"]
LK, LD, WK, WD, HK, HD = "ot_sram_1r1w_64x512_m1_r2c2", "ot_sram_1r1w_256x256_m2_r2c2", 171.288, 172.824, 77.784, 41.064
pre = {"l": "u_fcore.u_link.g_bank[%s].u_store.u_native.u_sram", "d": "u_fcore.u_land.g_bank[%s].u_mem"}
W = c["outline_um"][0]; out = []
for order, orient in ((["l3", "l2", "d0"], "MY"), (["l1", "l0", "d1"], "R0")):
    y = 15.12
    for k in order:
        w, h, mst = (WK, HK, LK) if k[0] == "l" else (WD, HD, LD)
        x = 15.12 if orient == "MY" else W - 15.12 - w
        out.append(dict(name=pre[k[0]] % k[1], master=mst, rect_um=[round(x, 3), round(y, 3), round(x + w, 3), round(y + h, 3)], orient=orient)); y += h + 8.64
old = {m["name"] for m in c["macros"]}; assert old == {m["name"] for m in out}, (old, [m["name"] for m in out])
c["macros"] = out; c["rule"] = "DIE-HBM-21 SRAM-edge rule probe RB (rd_out faces the centre channel; N-face logic field)"
os.unlink(f); json.dump(cm, open(f, "w"), indent=1); print([(m["name"][-22:], m["rect_um"], m["orient"]) for m in out])
