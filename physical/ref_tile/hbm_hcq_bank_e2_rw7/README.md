# hbm_hcq_bank_e2_rw7 -- HC ring edge bank e2 (ot_hbm_hc_bankq_ft_static lineage), H.STA.BLK.17.x  (HBM-COLLECT10/HCE2 10-21)
Top ot_hbm_hc_bankq_ft_rw7_static (core ot_hbm_hc_bankrc_core WROW 2, STG 1, CSPL 1). MAIN: row-0/1 clock entries (clk_w0/w1/d0/d1 S x 124..143; clk_e0/e1/x0/x1 S x 558..607) beside their row masses; clk_c S x 150, clk_ce S x 584; rows 2/3 keep N entries.

## Why
e2_rw4 (91d749022, ep9) FAIL CTS: clk_c boundary pin-flop spread 432.1 ps TT (60 boundary flops of 291: cd[0]/cv[0] at the W d_* pins,
cd[8]/cv[8] at the E o_* pins, fin_q NW corner, f_o NE corner; sink dump: cd chain 229 flops x 3..730 y 93..157). e2_rw4c (clk_c folded
into clk): clk 461.7. One root over a ~730 um register chain; pin moves cannot fix it.

## Structure (10-20 CLOCK RULE: regions <= ~400 um, landed crossings)
- W chain region clk_c: cv/cd stages 0..5 (taps 0/1/3 feed the STG-1 per-row copies) + chunked ring slots (ot_hcb_land_w per 8-bit chunk: kept registered slot enables, ot_pl_land_local_w calendar; own reset relay u_rst_l).
- E chain region clk_ce (new port, core clk_o; CPO 0): chunked ring read ot_pl_land_chunk_r K 2 = the o_* out registers. Slot = edge 6, read = edge 8:
  the ring replaces chain stages 6..8 exactly -> o_* age unchanged.
- f flag (f_in W face y 730 -> f_out E face y 730, sampled by the centre with leaf_v): D 4 / K 1 ring, slots written by the f_in pin on
  clk_w3 (= old fin_q edge), read on clk_x3 OR lf_any (= old f_o edge).
- x SRAM write copies on clk_x<h> (were clk_d<h>): clk_d<r> = row assembler + weight write copies (W column only).
- Offsets set at reset (rq re-registered from the same relay leaf rn_st on both sides), no flow control, no backpressure.
- SDC landing_mcp.sdc (sdc_extra): chain ring -> read -setup 2 -hold 3; f ring -> f_e -hold 3 (LANDING-CONTRACT L5, as lp.py).

## Added cycles for the HC ring schedule
0 added edges: o_* (v/ss/nv/wa/xa) leave at chain edge 8 as before; f_out = f_in(t-2) | lf_any(t-1) as before; SRAM read/write ages
unchanged (STG 1 copies load the same taps on the same edge, as rw5). RAW0 / HC_MIX_CYCLES unchanged.

## SAFE-DESIGN review (safe_1021, 8 points)
1 pins: RTL pin flops unchanged (chain cd[0] in, ring read out, f slots at f_in, write port, feed regs); region crossings landed: PASS
2 reach: chain W->E (~700 um) and f W->E (~715 um) now landed (K 2 = 2T window; f K 1 = 1T as before, hold-tolerant); residual
  pre-existing single-cycle cross-root hops cd[0] -> x-row copies (~580 um, 11 b) and leaf lf -> f_e: judged by gate/route STA (waived, rule freeze)
3 fanout: ring select one-hot -> 29 loads, slot enables 29, rn_st/rn_g relay leaves unchanged class: PASS by construction (native census in the gate)
4 depth: ring read = 4:1 AND-OR, rest plain registers: PASS
5 storage: SRAM macros unchanged; ring 4x29 + 4x1 flops (< 2 kb): PASS
6 floorplan: outline 734.4 square fixed by the die slot / neighbour faces (macros + 8 leaves on the 43.2 lattice), util ~51 %: PASS (unchanged)
7 clock: W/E chain regions each <= ~370 um with entry beside the mass; every chain/f crossing = landing ring; 80 ps inside a region: gate --cts
8 reset: only control/valid reset (cv, ring counters/valid, f_e); data (cd, slots) unreset; ring rq landed per region from rn_st: PASS
Native census: in-gate (pre_route_gate synth native_census, limit 32) before floorplan.

## Bench (Verilator 5.050, ot-run): HC_XDEF +HC_BANK_RC +HC_BANK_RW5 +HC_BANK_RW7 (b0/cb rw5 + e2 rw7)
m0 PASS expected; mut1 (bank 3 weight rotation), mut5 (bank 3 landing copy), mut6 (e2 chain ring K 3) FAIL. Witnesses results/rtl/hbm_hc_ring_1021_rw7.
