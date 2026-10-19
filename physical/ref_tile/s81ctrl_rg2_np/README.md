# s81ctrl_rg2_np -- dsfd_ctrl_rg2, flop-first pins without protected hold pads (S81-CTRL-SVC 10-19)

Root cause of the 8a9 / 7a5 CTS failures (ODB-0373 "Attempt to connect iterm to dont_touch net ot_inhold_n00001"):
the recipe-2 pin hold pads (inhold/outhold) put 1,243 dont_touch HB2 pad -> BUFx4f driver pairs on the input pins.
Setup repair's CloneMove clones the driver and tries to connect the clone to the protected pad net
(isolated in results/rtl/s81_ctrl_safe_1019/protected_driver_failure/move_isolation: CloneMove-only reproduces it,
SizeUp/Buffer-only do not). The pads are redundant here: every pin is a flop at its face in its own clock domain
(RTL), anchored by io_flop_at_pins. Fix = remove the pads (inhold/outhold false), so no protected net exists for any
repair move; boundary hold is repaired by ordinary buffers at io_hold_margin 0.03. Sources/geometry otherwise equal to
s81ctrl_rg2_sram (four real dualclock 16x546 SRAM FIFOs, 531.25 x 302.4).

## Safe-design checklist (owner 10-19)
1 Pins: PASS -- RTL face flop on every pin (rq/rd/rk/wd/status on clk, PHY k_*/kr_* on ckh); reset_landing 2 stages (clk).
2 Reach: PASS (pre-gate) -- per-PC paths <= 266 um in the 4-SRAM layout; placed reach checked by the gate.
3 Fanout: PASS -- kept per-32-bit enables / one-hot reads (S81-SAFE-FIX); no >32-load critical register found.
4 Depth: PASS -- textbook depth 375 ps.
5 Storage: PASS -- four >2 kb FIFOs are real dualclock SRAM macros (no runtime-indexed flop arrays).
6 Floorplan: PASS with waiver -- macros on the 43.2 lattice, full-width std band, aspect 1.76; std util ~1.3% is the
  PHY-face slot (2,575 N+S pins at ~2.5 pins/um set the width, SRAM stack the height); slot change 250 -> 302.4 owed.
7 Clock: PASS (to confirm at CTS) -- two roots clk/ckh each beside its register mass, real Gray CDC; spread target
  <= 80 ps TT+FF; io_hold_margin 0.03.
8 Schedule: PASS -- static; SRAM FIFO cycle-exact vs the flop FIFO (crossing metrics 6.95/5.26 identical, full 32-PC exact PASS).
