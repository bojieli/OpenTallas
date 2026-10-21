# qfd_tt_head_static_h16x -- h16v successor (QW-H16X 10-20), TOK.QW.LAYER.3.SEG head leaf: depth round 2

h16v gate (CTS ODB, TT placement RC, signoff.sdc; worst endpoints grouped by RTL register in
h16v_violators_by_rtl.txt):
- macro->reg -321.5 (263 paths): program SRAM rd_out -> prog_q.  rd_out clk->q 430 ps (254 ps slew on the macro clock pin) +
  ~560 ps wire/buffers to prog_q flops placed at their consumers (the FIFO write) + 2 gates.
- reg->reg -282: fixed-issue index -> next_from_rom select -> next_row mux -> 32-bit KS compare -> core_fault (30 levels).
- -224 gdesc_q -> g_present 32-bit compare -> sel_g -> calendar read q; -151 q_pw_addr -> row decode -> 376 row enables
  (475 ps broadcast wire); -158 q_pos -> dts quotient -> pq_r (fanout/slew).  Rest -127..-1 (controller st cones, FIFO
  rd_out -> tq0/tq1, ~100-130 ps clock skew on the fixed-issue cluster).

RTL (H16X = 1 on ot_qfd_tt_ctlm_static_hr_safe32; default 0 = h16v; all exact, 0 edges):
- head rk: the program-store read is issued ONE EDGE EARLY -- controller prog_ce_pre (the fetch condition without !fin) and
  address prog_base + fpc (= q_prog_base + prog_addr on the fetch edge; u_isd has no reset) -- and rd_out lands in a raw
  capture register p_cap (1024 kept flops, rd_out -> D with no logic); prog_q <= p_cap on the unchanged edge.  prog_q,
  the FIFO and every consumer keep their timing.  Simulation checks: early read == as-built read every fetch; no program
  write of the row in the early-read edge (contract: boot load only).
- fixed issue: next_row > cycle as a late select of two parallel KS compares (slot_q / tail); g_present registered with
  gdesc_q; the calendar row write select registered one edge early from pw_addr (u_isd input) -> one-hot row strobes.
- controller PQP: the dts quotient from pos one edge early (pq_p), pq_r <= pq_p on start.
RTL parent bench (qfd_tt_ctlm_dv + safe32 head RTL H16X=1 with all reference $fatal checks) V5.050: img0 PASS 123/123,
imgh PASS 131/131 (results/rtl/qw_head_safe32_1020/h16x/run_rtl_parent.sh).

Netlist: results/rtl/qw_head_safe32_1020/h16x/run_gen.sh (h16v chain, prepare_generic -chparam H16X 1, ABC &if -g/&synch2/
dch/map -D 1 = h16v's): bounded max depth 20, 0 flops over 20 (7176 flops); 25,199 bounded cells; load cap 16 internal / 32
input, max data-reset loads 32.  h16xb = the same netlist at route.pd 0.7 (parallel fallback: std cells are ~11% of the
placeable area and PD 0.5 spreads them, h16v's worst reg->reg paths carry 200-475 ps single wires).

## SAFE-DESIGN checklist
1 Pins: pin registers ON (ck_head); reset landed by the kit (2 stages) -- PASS (as h16u/h16v)
2 Reach: 345.6 x 302.4 leaf, no planned wire > 405 um; the SRAM read data now has a capture flop at the macro -- FIXED
3 Fanout: bounded netlist load-cap 16 (32 input / reset) -- PASS by construction; gate native census (limit 32)
4 Depth: bounded max 20 levels; h16v violator groups prog_q / core_fault / q / grows / pq_r restructured -- FIXED (gate)
5 Storage: FIFO 6x 32x128 SRAM + 2x 64x512 program store; new regs p_cap 1024 b (pipeline data, not storage), own/g one-hot
  16 b, gp_r 1 b, pq_p 18 b -- PASS
6 Floorplan: h16u/h16v geometry (8 macros on the 43.2 lattice), E face pin-bound -- WARN (unchanged)
7 Clock: single CTS root ck_head (flops + 8 SRAM clock pins), no crossing -- gate
8 Schedule: 0 added edges (early read keeps prog_q timing; all other cuts register pure functions of next values) -- PASS;
  nothing to price (no NOTICE to QW-TOKSCHED / CTLM calendar needed)
Parent: qfd_tt_ctlm_dv u_hr drops .ck_pm0/.ck_pm1 (1r port list), as prepare_bench.py does.
