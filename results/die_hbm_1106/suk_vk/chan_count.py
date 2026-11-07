#!/usr/bin/env python3
"""Nets vs channel tracks for the part55 SU lane form (COORD 22:35).  chan_count.py PLAN_DIR.  Tracks x 0.74 (GRT layer adjust measured on vF:
1528857 -> 1141253 M4, M5 stripes included there).  M4/M5 0.048, M6 0.064.  Net counts from the synth netlist of vF/vD (6 macros): 1536 rd_out, 8 mask
and 32 wd nets on both faces, 49 shared addr/ctl nets, 204 tied repair pins on the far face."""
import json, sys
pd = sys.argv[1]; C = json.load(open(pd + "/core_macros.json"))["cores"]; AD = 0.74
trk = lambda um, p: int(um / p * AD)
H, CY0, CY1 = 207.36, 30.96, 176.424
for m, c in C.items():
    if "su_pg_lane" not in m or "_x_core" not in m:
        continue
    W = c["outline_um"][0]; R = [x["rect_um"] for x in c["macros"]]; xs = sorted({r[0] for r in R}); xw, xe = xs[0], xs[1]; MW = R[0][2] - R[0][0]
    pf = json.load(open("%s/cores/%s__%gx%g__d44v_p55.json" % (pd, m, W, H))); P = pf["pins"] if isinstance(pf, dict) else pf
    wp = [p for p in P if p["x"] < 1 and p["name"] != "clk"]; np_ = [p for p in P if p["y"] > H - 1]; sp = [p for p in P if p["y"] < 1]
    lc, rc = xw + MW, xe
    ctr = (lc + rc) / 2
    print(m, "outline", W, H, "columns x", xw, xe, "channels: W far %.2f centre %.2f E far %.2f" % (xw - 4.32, rc - lc, W - 4.32 - xe - MW), "pins W/N/S", len(wp), len(np_), len(sp))
    print("  W far channel vertical M5 cap", trk(xw - 4.32, .048), "need <=", 120, "(40 wd/mask trunks + fanout-8 leaf spans) +", 20, "W-pin jogs at a cut")
    print("  E far channel vertical M5 cap", trk(W - 4.32 - xe - MW, .048), "need <=", 120)
    print("  W col crossing, M6 per macro row: cap", trk(41.064, .064), "need", round(len(wp) * 41.064 / 198.72) + 14, "(W pins + wd/mask)")
    print("  E col crossing: 0 rd_out, 0 pins (no E pin field); E far 40 nets via row gaps/bands: M4 row gap cap", trk(11.136, .048))
    print("  centre mouths per row per column: M4 cap", trk(41.064, .048), "rd_out 256 + addr/ctl ~16 + wd/mask ~14 =", 286)
    h = trk(rc - lc, .048)
    print("  centre vertical at a row boundary: M5 cap", h, "need <= 512 (two rows of rd_out if all muxed at mid-height; M3 not counted)")
    print("  centre horizontal: M4+M6 cap", trk(CY1 - CY0, .048) + trk(CY1 - CY0, .064), "rd_out 1536 + rest ~150")
    for nm, ps in (("N", np_), ("S", sp)):
        l = sum(1 for p in ps if p["x"] < lc); r = sum(1 for p in ps if p["x"] > rc)
        band = CY0 if nm == "S" else H - CY1
        print("  %s band: pins left of centre %d, right %d, cut cap M4+M6 %d (M5 straight down across macros + row gaps extra)" % (nm, l, r, trk(band, .048) + trk(band, .064)))
