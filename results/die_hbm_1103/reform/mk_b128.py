#!/usr/bin/env python3
"""DIE-HBM-61/B128 d44v part 5 (one-block fix after freeze, COORD 15:3x GEOM): macro sites of the bank128_pair
cores (ot_hbm_hc_bank128_pair_core, kit variants __v7d149b37532c / __v9bf80cdae38d, and ot_hbm_hc_bank128_pair_first_core;
the only d44v cores with this 1024x256 + 128x256 + 1024x256 stack).  Outline 250.56 x 267.84 and plan pins kept
(N 563 M5 x 8.9-241.7, W/E 512 full height, S 2, clock entry (125.3, 133.9)).
  Kit d44v AUTO-GEOM (intel2 kit-wave item __v7d149b37532c): GRT overflow 7646 at 50 it, channel_h FAIL 0.93 in the
  N band, channel_v / col_v FAIL 0.67 in the W column at y ~207.  Cause: g_w[0] at y 179.28-249.77 left an 18 um N
  band (core 9.5 um of rows) under the 563 N face pins; their face flops route out sideways around the macro corners
  (macros block M1-M4, only M5 crosses).  Both 1024 macros sat at x 21.6, so the W column was 17 um of rows for the
  512 W pins + the macro W-edge pins.
  LEF: the SRAM signal pins are M4 on the W and E edges of the master (415 + 415 per 1024x256, 410 + 411 per 128x256),
  in its lower 40.5 um (R0); MY/R0 keep them low, R180/MX put them high.  So the channels that carry macro pins are
  the W/E columns, sized here from pin count (macro side pins + slot side pins) x 0.048 M4 pitch / 2 >= 22 um.
  Form (S edge stack, wide N band, centred 1024 columns):
    g_w[1] 1024x256 R180 at (38.88, 4.32)   S edge (S face has 2 pins), pins high into band A
    g_x[0] 128x256  MY   at (21.6, 108.0)   x kept: the clock entry (125.3, 133.9) stays 8.9 um E of it
    g_w[0] 1024x256 MY   at (38.88, 158.76) 9.7 um above g_x[0], pins low (W/E columns, away from the N band corners);
      N band 38.6 um (was 18.1), band A 33.2 um
  W column 38.88 (was 21.6), E column 36.94 (was 54.2) beside the 1024s.
  Probe (epyc2 b128probe, kit d44v synth, 3_place + AUTO-GEOM GRT M2-M5 50 it): old 7646 -> this form 0 (usage 39.6%,
  channel_h WARN 0.999, r2r 1 capture 422 um advisory); alt g_w[0] R180 (pins up) also 0 but usage 41.3%, channel_h 1.03,
  r2r 2 captures 434 um.
Writes core_macros.json cores[<module>] (old entry kept under previous).     python3 mk_b128.py PLAN_DIR"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); f = d / "core_macros.json"; C = json.loads(f.read_text())
r3 = lambda v: round(v, 3)
M1K, M128 = ("ot_sram_1r1w_1024x256_m2_r2c2", 174.744, 70.488), ("ot_sram_1r1w_128x256_m1_r2c2", 94.824, 41.064)
def mac(name, m, orient, x0, y0):
    return dict(name=name, master=m[0], orient=orient, rect_um=[r3(x0), r3(y0), r3(x0 + m[1]), r3(y0 + m[2])])
B = "u_fcore.u_c.u_b."
NEW = [mac(B + "g_w[1].u_m", M1K, "R180", 38.88, 4.32), mac(B + "g_x[0].u_m", M128, "MY", 21.6, 108.0),
       mac(B + "g_w[0].u_m", M1K, "MY", 38.88, 158.76)]
ENT = (125.3, 133.9)
for M in ("ot_hbm_hc_bank128_pair_core", "ot_hbm_hc_bank128_pair_first_core"):
    old = C["cores"][M]; W, H = old["outline_um"]; ex, ey = ENT
    assert [a["name"] for a in old["macros"]] == [a["name"] for a in NEW], M
    for a in NEW:   # inside the outline with the 4.32 edge, 8.64 apart, clear of the clock entry by the 4.32 halo
        x0, y0, x1, y1 = a["rect_um"]
        assert x0 >= 4.32 and y0 >= 4.32 and x1 <= W - 4.32 and y1 <= H - 4.32, (M, a)
        assert not (x0 - 4.32 < ex < x1 + 4.32 and y0 - 4.32 < ey < y1 + 4.32), (M, a)
        for b in NEW:
            if b is a: continue
            u0, v0, u1, v1 = b["rect_um"]
            assert min(x1, u1) - max(x0, u0) < -8.63 or min(y1, v1) - max(y0, v0) < -8.63, (M, a, b)
    e = {k: v for k, v in old.items() if k not in ("previous", "sources", "macros", "basis", "status")}
    C["cores"][M] = dict(status="KNOWN", outline_um=old["outline_um"], basis=(
        "DIE-HBM-61/B128 d44v p5: S-edge stack g_w[1] R180 / g_x[0] MY / g_w[0] MY, N band 38.6 um under the 563 N "
        "face pins (was 18.1), 1024 columns centred (W column 38.88 for 512 W + 415 macro-edge M4 pins); macro pins "
        "are W/E-edge M4, channels sized from pin count; clock entry (125.3, 133.9) clear; outline and pins kept"),
        macros=[dict(a) for a in NEW], channel_rule_um=old.get("channel_rule_um", 10.8),
        previous={k: v for k, v in old.items() if k != "previous"}, **{k: v for k, v in e.items() if k not in ("outline_um", "channel_rule_um")})
    print(M, old["status"], "->", "KNOWN", len(NEW), "macros")
f.unlink(); f.write_text(json.dumps(C, indent=1) + "\n")
