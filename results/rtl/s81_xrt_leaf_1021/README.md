# STW-S81-COLLA 10-21: xrt1 / xrt3 leaf kits (S81 slice u_xr successor, TOK.DS.BENCH.4.2 FFN result transport)
Kits: s81sl_xrt1 (MAIN, FOREG 0, xr1f outline 311.04x395.28), s81sl_xrt1_b (FB, FOREG 1, 345.6x432),
      s81sl_xrt3 (MAIN, FOREG 0, xr3 outline 570.24x395.28), s81sl_xrt3_b (FB, FOREG 1, 596.16x432; < 600 um clock span).
RTL: rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv (main, RG-FFN 59a8155d3), same ports as xr1/xr3; geometry/pins/recipe from the CLOSED
xr1f (12b616b54) / xr3 (e656ad73c) kits; FB pin ranges scaled per face with the outline.
Benches (Verilator 5.050, ot-epyc5, tools/s81_slice/xrt_bench.sh = RG-FFN ub_xr.sh recipe), FOREG 0 and 1 both:
 base hb0/hb1 x seeds 1,2 PASS; mutants hops(h0 err 784, h1 737) row(1599) porder(1016) xhold(5668) nocol(XRILL 1/13) bwide(XRILL 1/14) FAIL.
 Witnesses bench/f<FOREG>_<case>/run.log + verdict.out.
Native census (RG-FFN, FOREG 0): xrt1 max 32 / 0 > 32 / rst_n 16; xrt3 max 32 / 0 / 16. The gate re-runs the census on each kit.
FOREG 1 (FB) = dedicated fault output flop, +1 fault-visibility cycle; a parent binding the FB view builds with +define+OT_S81SL_XR_FOREG.
