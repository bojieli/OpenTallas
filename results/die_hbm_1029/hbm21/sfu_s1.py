#!/usr/bin/env python3
"""DIE-HBM-21: SRAM-edge rule for sfustore in a plan dir (in place): column orient [R0, MY, R0], col2 abuts col1 at the
6.48-um gap of the measured S1 probe, col3 right-aligned at 15.12 (rd_out of col2+col3 face the 41.7-um centre gap)."""
import json, os, sys
d = sys.argv[1]; f = d + "/core_macros.json"; cm = json.load(open(f))
c = cm["cores"]["ot_hbm_su_static_sfustore_hw"]; W = c["outline_um"][0]; MW = 94.824
xs = sorted({m["rect_um"][0] for m in c["macros"]}); assert len(xs) == 3, xs
nx = {xs[0]: (15.12, "R0"), xs[1]: (15.12 + MW + 6.48, "MY"), xs[2]: (round(W - 15.12 - MW, 3), "R0")}
for m in c["macros"]:
    x, o = nx[m["rect_um"][0]]; r = m["rect_um"]; m["rect_um"] = [round(x, 3), r[1], round(x + MW, 3), r[3]]; m["orient"] = o
c["rule"] = "DIE-HBM-21 SRAM-edge rule (rd_out faces logic): cols R0/MY/R0 at x 15.12/116.424/%.3f; probe S1 GRT 0 (vA 13), relay_collapse 0" % (W - 15.12 - MW)
os.unlink(f); json.dump(cm, open(f, "w"), indent=1); print(sorted({(m["rect_um"][0], m["orient"]) for m in c["macros"]}))
