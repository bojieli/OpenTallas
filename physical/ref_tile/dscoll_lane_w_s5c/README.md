# dscoll_lane_w_s5c -- S81-COLL v8 lane tile, budgeted std band + face columns (S81-COLL5, S81.STA.LKTO.2, 10-20)

Top `dsfd_coll_lane_w_safe4` with defines OT_COLL_NATIVE32 + OT_COLL_NATIVE32_OFF (v8, branch claude/s81-coll4-1020
@30ea2ab80; evidence results/rtl/s81_coll_native32_1020/native_v8/README.md), CH_BOARD 700. Clock: TritonCTS sink-clustered tree (clock "cts"), parallel fallback of the spine variant (owner 10-19 parallel routes).
Generator results/rtl/s81_coll_native32_1020/kit_s5/gen_s5_specs.py (base = dscoll_lane_w_s4b spec, macros unchanged
except the N strip one lattice step up); row hook physical/dscoll_cx/coll_s5_cell_band.tcl (sourced at the end of place.tcl).

Why (structural redesign after 4 terminal s4/s4b placement FAILs, ../s4_terminal of native32 evidence): the std region was
one 28.8-39.6 um band sized at 40-60% of the SYNTHESIS std area only. Post-place std was already 12.1k um2 (60% of the
band) and OT_SPINE added 4-34k clock cells; the ~2,130 W/E face bus pins pulled their cells into the two band ends
(rowless face channels). s5 budgets the band for synthesis + repair + spine and gives the face pins their own rows.

Geometry 725.76 x 583.2 (aspect 1.24). S strip unchanged (RX FIFO 18 x 256x64 + credit-rx landing 9 x 32x64, MX/R180);
N strip (gearbox 10 x 32x64 + replay 18 x 256x64) at y 345.6..518.4. Std region = ONE full-width band y 259.2..340.2
(81 um) + two full-height face columns x 2.16..37.8 and 688.0..723.6 joined to it (one contiguous region, no island).

## SAFE-DESIGN checklist (owner 10-19) + pre-gate native census
1 Pins: PASS -- every data pin registered in the safe4/v8 RTL; reset_landing 2 stages (rs).
2 Reach: PASS by construction -- macro->band <= 220 um; pin cells in the face columns at their pins; face->band <= 260 um.
3 Fanout: PASS -- v8 mapped census (same RTL/defines/keep modules) 0 roots > 32, max 32; actual-Liberty native census PASS
  48,713 roots max 32 (native_v8/coll_census.json, actual_roles_summary.json). Kept modules unchanged.
4 Depth: PASS -- 540.1 ps / 14 levels (native_v8/textbook_native.json) <= 600.
5 Storage: PASS -- all storage in 55 bank64 SRAMs.
6 Floorplan: macros on the 43.2 lattice (all origins multiples of 43.2), >= 20 um channels, core-edge channels 41 / 41 um,
  no macro in the band; std band 81 x 721.4 = 58.4k um2 sized from the BUDGETED std area ~18.6k um2 (synthesis 9,489 +
  place repair ~2.6k measured W_s4b + spine/CTS ~4.5k + hold repair ~2k) = 32% (synthesis alone 16%); face columns
  +36k um2. Fill 17% overall is lattice/channel area (WARN, as s4b). Pins full W/E faces <= 1.9/um (<= 6/um).
7 Clock: TritonCTS sink-clustered tree (clock "cts"), parallel fallback of the spine variant (owner 10-19 parallel routes); ck pin at the band centre y 299; io_hold_margin 0.03; pin-flop spread judged by the --cts gate (TT/FF <= 80).
8 Schedule: PASS -- static, 0 added cycles (v8 keeps snd-una as state); v8 miter m0 PASS 79,994; m1-m4 FAIL witnesses
  native_v8/bench/m1..m4.log.
