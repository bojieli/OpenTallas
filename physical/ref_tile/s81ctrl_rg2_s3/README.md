# s81ctrl_rg2_s3 -- dsfd_ctrl_rg2 SAFE successor (LEAD2-S81/LINK-CTRL 10-19, tree S81.STA.OWN.9)

Base: codex/s81-ctrl-clock-export-1019 b91a2773d (s81ctrl_rg2_np + explicit `-master_clock core_clk` on ck_o_fwd;
native export proof PASS). s81ctrl_rg2_np's route ended NEEDS_HUMAN (export) and its four stock 16x546 dual-clock
masters had 825 contacts per 81 um W/E face = 10.19 pins/um (> 6, SAFE item 6). Tools from origin/main.

## SRAM-bank audit (choice)
| variant | macros | macro area | W/E face pins/um | max placed stage span | FIFO ctrl fanout to banks |
|---|---|---|---|---|---|
| np stock 16x546 | 4 | 57,317 um2 | 10.19 FAIL | (gate +99 ps r2r, row-per-PC vs W/E pin halves) | 1 |
| Codex bank64: 22 x 32x64 (e26d92503 / 69d92c0a2) | 22 | 12,179 um2 | 5.95 PASS | 57 spans > 405 um, worst 495.9 (placed replay) FAIL | 6 (req) / 5 (resp) |
| plain split 2-3 x 16x273/182 at stock pitch | 8-12 | -- | ~10.2 FAIL (pin-limited height scales with pins) | -- | 2-3 |
| **s3: 4 x 16x340 wide pitch 0.192 um (chosen)** | 4 | 46,117 um2 | **5.12 PASS** | per-PC column under own pin half; placed replay at gate | 1 |

The stock compiler stretches a pin-limited master to the pin count at 0.096 um, so splitting keeps ~10/um; only a wider
pitch (or a deeper array) passes. s3 = same compiler (tools/mem_compiler/build_wide_pitch_2c_1019.py), pitch 0.192 um
(every 4th M4 track), 114.48 x 100.71 um, 516 contacts per W/E face. 340 = request width; response (277) uses the same
master (one tile variant). RTL: `S81CTRL_SRAM_P192` in ot_s81ph_afifo_g_sram.sv picks the master; FIFO logic, read/write
edges and the schedule are unchanged (0 added cycles).

## Floorplan
531.25 x 324.0 um (width = PHY PC pitch; height = two 100.71 macro rows on the lattice + face bands), aspect 1.64.
PC0 column x 86.4 (resp y 43.2, req y 172.8), PC1 column x 345.6 (same rows): each PC's FIFOs sit under that PC's W/E
pin half of the N (rq/rd) and S (PHY) faces. Channels W 86.4 / middle 144.7 / E 71.2 um; full-width std rows
y 0-43.2, 143.9-172.8, 273.5-324 plus the three channels.

## Safe-design checklist (owner 10-19)
1 Pins: PASS -- RTL face flop on every pin in its own domain (flow pin-reg hook off: it clocks one domain only; reason in spec); reset_landing 2 stages.
2 Reach: PASS pre-gate (to confirm by placed replay) -- per-PC column below its own pin half; face-flop -> macro pin bbox <= ~270 um vertical + <= ~180 um horizontal; no cross-PC wire. Bank64 alternative had 57 placed spans > 405.
3 Fanout: PASS -- kept per-32-bit enables / one-hot reads as np; one macro per FIFO (no bank-control fan-out).
4 Depth: PASS -- same logic as np (textbook depth 375 ps; np gate r2r +99 ps).
5 Storage: PASS -- four > 2 kb FIFOs are dual-clock SRAM macros.
6 Floorplan: PASS with waiver -- macros on the 43.2 lattice, macro faces 5.12 pins/um, halo 5.4, full-width std rows,
  aspect 1.64; WAIVER: std util ~2 % is the PHY-face slot (2,575 N+S pins over the 531.25 PC-pitch width; height set by
  the two macro rows), not a sizing choice. Slot change 250 -> 324 um height owed to the die floorplan (slot_change_request).
7 Clock: PASS (confirm at CTS) -- clk / ckh roots beside their register masses, Gray CDC, explicit ck_o_fwd master
  (b91a2773d); spread target <= 80 ps TT+FF; io_hold_margin 0.03.
8 Schedule: PASS -- static, cycle-identical to np (same FIFO RTL; only the master changes); cycles_added 0.

## Gate 1 (44fab881b, agidock128 ref_gate/s81ctrl_rg2_s3-20261019-163603): FAIL 2 -> fixed in spec
- clock_rule: core_clk 1,390 sinks, TT/FF insertion 458.6/383.4 ps, pin-flop spread 99.7/92.8 ps > 80 (np had 42.8): the
  H-tree leaves string across the 531 um N face and the macro clock pins share high-slew (~330 ps) leaf nets.
  Fix: route.cts_sink {size 20, diameter 40 um, -sink_clustering_levels 2 -distance_between_buffers 40} (qkd_astk_ep precedent).
- fill 28% < 35%: pin-bound (N 1246 / S 1321 pins over 98% of the 531 um faces) -> fill_reason.pin_bound recorded.
- Otherwise: textbook depth 375 ps PASS, 0 x-clock violations, GRT setup repair converged positive; PNGs viewed
  (results/rtl/s81_ctrl_rg2_s3_1019/gate1_fail/{floorplan,density}.png): 4 macros in two per-PC columns on the lattice,
  std mass at N/S faces and macro W/E channels, full-width rows.
- Benches (5.050): exact PASS (crossing latency 6.95/5.26 cks = np, cycle-identical), MUT_PACK FAIL errors=5910 (witness committed).
