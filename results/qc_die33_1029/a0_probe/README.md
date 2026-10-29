# DIE-QC-33 A0 NK r2 GEOMETRY PROBE (graph homes, current RTL; no CTS, no sign-off use), 2026-10-29 10:07 PDT
Unit oth-ubuntu-421792-1793292251 (intel2). Kit: /srv/opentallas-scratch2/claude/die-qc33-a0/kits/qfd_tile_nk_a0c_a0nk14icg2r2 = Codex r1 kit + graph_homes.tcl (12,811 FIRM homes, then released for DPL) with the NL anchor line removed. GPL converged at overflow 0.21. DPL passed with 0 overlaps (failed r1 kit: AUTO-GEOM FAIL on reach; NL r1: DPL-0033).

AUTO-GEOM (`auto_geom.json`/`auto_geom.png`, VIEWED: macros legal, 0 cells on macros, FFs in the streets):
`AUTO-GEOM FAIL aspect=FAIL(2.528) partial_face=FAIL(2) channel_h=FAIL(0.8) channel_v=FAIL(1.72) col_v=FAIL(1.91) clock_reach=FAIL(748.53) grt=NA(None) outline=ok(457.92x1157.76) fill_hi=ok(0.0366) pin_reg_p90=ok(8.17) pin_reg_max=ok(139.83) pin_unreg=ok(0) r2r=ok(402.95) r2r_count=ok(0) pin_density=ok(5.3) std_band=ok(1.0) cells_on_macros=ok(0) relay_collapse=ok(0) blocked_h=ok(0) blocked_v=ok(0) clock_on_macro=ok(0) comb_loops=ok(0) clock_rooted=ok(0) clock_sinks=ok(15376)`

| item | r1 (failed) | r2 probe | analytic plan |
|---|---|---|---|
| r2r captures > 405 | 532 (max 657.45) | **0 (max 402.95)** | 0 (395.00) |
| relay collapsed | 7 | **0** | 0 |
| ICG enable legs > 405 (100 legs) | 7 (main 548.53) | **0 (max 395.55)** | 0 (395.8) |
| pin_reg_max (rst_n) | 261.76 FAIL | **139.83 ok** (p90 8.17) | open |
| rst_n -> ASR hop/dr flops (raw rst_n, current RTL) | <=357 | max 358.5 | the RTL fix ICG_RRST moves them off rst_n |

Still FAIL, outside the reach repair: aspect 2.528 (plan outline), partial_face 2 (plan pins), and the channel estimates h 0.8 / v 1.72 / col_v 1.91 (est., GRT decides). clock_reach 748.53 is a CTS item.
