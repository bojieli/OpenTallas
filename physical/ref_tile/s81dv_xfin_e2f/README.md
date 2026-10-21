# s81dv_xfin_e2f -- ot_s81dv_xfin ENG-mode re-close (FALLBACK)  [S81-SLICE/CHILD 10-21]

Why: the bound closed view physical/ref_tile/s81dv_xfin/views/ot_s81dv_xfin (x5, closure s81dv_xfin-x5-06cb91161, 181.44^2,
std 16108 um2) predates 269ef81a1 (xfin ENG mode: ports mode, e_v, e_c, e_hh, e_kk, e_dd; 4 x ot_s81dv_eng_finish).
The k8 slice parent gates fail in yosys ("ot_s81dv_xfin has no port e_dd"). Re-close on current RTL; no aliasing.
RTL unchanged (rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv @ origin/main 81add7c46). Benches/mutants = the RTL-BUILD-S81 set
(norm16 base/mutbase/mutleaf + xfin16e base/mutetag/muteassoc), committed witnesses (5.050 for the ENG mutants).
Outline: 388.8 x 475.2 (+55% area, util ~0.34-0.45 at 60-80k um2; W-E 388.8 keeps the ring pass-through hop < 405 um). Pins: ring wi/wo W (lower part), ei/eo E, s_*/rb N, clk/rst/go/mode/sid/eps/fault S;
e_* (registered outputs e_v/e_c/e_hh/e_kk/e_dd) on the W face upper part, toward u_eg (region C, west of u_xf in the k8 plan).
Parent kit must take: new outline, new pin faces (e_* W instead of N), view path physical/ref_tile/s81dv_xfin_e2f/views/ot_s81dv_xfin.

## SAFE review (8 points, safe_1021 + 10-19 checklist)
1 Pins: PASS -- source-registered: every input captured in a flop at the pin (go/mode/eps/s_*/sid capture, xstop wi/ei flops), every
  output a flop (eo/wo/rb/e_*/fault); io_flop_at_pins anchors them at the faces. Reset: RTL 2-stage rs landing + kit reset_landing 2 stages
  (+2 reset-release cycles, one-time, not on the token path; priced as a reset-schedule constant). Faces <= 1.8 pins/um.
2 Reach: PASS -- longest single-cycle wire = ring W->E pass-through <= outline width (388.8 um < 405).
3 Fanout: WAIVED (rule freeze 10-20 09:35: tile rules guidance, die results decide) -- go_t in each eng_finish fans to ~1300 vld/iss/rdy/win
  bits, the registered flit fields id/it/ib to 48-240 leaves; all are register-driven full-cycle nets the tool buffers. Same structure as
  ot_s81dv_norm_finish which closed in x5. Structural fix if the route fails: per-tree kept go_t copies (16/tree) + per-tree flit-field copies.
4 Depth: PASS (to be confirmed by the gate) -- issue = registered 8-group one-hot + 48-group priority + 384:1 AND-OR operand select, then
  the pipelined qadd (LA 6). Fallback if TT fails: register win before the operand mux (+1 cycle per add, priced: 3 x 79 adds/copy -> +237 cycles).
5 Storage: WAIVED -- 12 x (80 leaves + 79 nodes) x 32 b = ~61k flops are the fixed golden-heap reduction nodes (one static node per
  register, written once per go, bit-exact association with hdc_golden_v41), not a runtime-addressed array; NORM finish (same pattern) closed.
  Structural alternative if the route fails: SRAM-backed node store per copy (ot_sram_1r1w) with a static issue schedule.
6 Floorplan: PASS -- no macros; outline from the synthesis-area estimate at util ~0.52 (MAIN) / larger FALLBACK; aspect 1.22; full std-cell band.
7 Clock: PASS -- one clock (clk), one region, centre-fed CTS; pin-flop spread <= 80 ps TT+FF judged by the gate; io_hold_margin 0.03 (was 0.0).
8 Schedule: PASS -- static (no credits/backpressure; ring slot fill forwards first, deterministic). No added datapath cycles (RTL unchanged).
