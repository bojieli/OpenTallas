# qfd_dv_s5_red2b -- SU reducer leaf red2 (QW-SLICE7-LEAVES/SCRED, Q.STA.SLICE.2)

Successor of qfd_dv_s5_red / qfd_dv_s5_redb (claude/qw-slice6-scred-1019 94483a34c), whose gate WARNs did not qualify:
ASAP7 mapped census reset 740-763 / data 504 loads, TT stage estimate 775-814 ps (FP add/mul LAT 3).
Outline 280.8 x 194.4 (util 0.39, aspect 1.44) -- parallel fallback, same netlist. Main kit qfd_dv_s5_red2, fallback qfd_dv_s5_red2b.

RTL: top `qfd_dv_s5_red2_leaf` = `rtl/qwen_dv/s5/qfd_dv_s5_red2_k79.sv` (+ _helpers): the bounded constructor netlist of
`qfd_dv_s5_red2 #(LA 7, LM 9)` (rtl/qwen_dv/s5/qfd_dv_s5_red2.sv: bit-identical ot_hdc_fp32_add_lat/_mul_lat with DRST 0,
kept exact-age rings for every delay line >= 3, face in/out registers) built by tools/qwen_dv/bound_math_netlist.py
--load-cap 8 --transparent-inverters --retain-mux --shared-helpers --retain-keep (new flag: keeps the Kogge-Stone (* keep *)
levels, otherwise ABC re-ripples the carries: LA7/LM6 828 ps -> 667 ps with it).

## Pre-gate native census (ASAP7 RVT TT mapped, results/arch/qw_slice6_1019/scred2_1020/native_red2_k79/)
0 non-clock roots > 32 (raw inputs + reset included), max 24 loads, raw rst_n 2 loads; TT stage estimate 556.8 ps / 17 levels;
34,272 FF; Liberty area 21,417 um2 (old red 11,913 FF / ~10.3k um2); boundary levels in->reg 0, reg->out 0, in->out 0.
Mapped SHA256 b0add102910015af289201ff699258f96bafd5dbd5cae0e39e193c9133b3ee6e. Sweep (bounded, depth ps): LA4/LM4 910,
LA6/LM6 910, LA7/LM6 822 (667 with --retain-keep, 647 cap 8), LA7/LM9 cap 8 + retain-keep 557 = this kit.

## Benches (Verilator 5.050, fleet)
RTL: rtl/test/qwen_dv/s5_scred2/run_red2.sh -- red2 vs ORIGINAL qfd_dv_s5_red, 3000 random segments (SUM / MAX / SQ, 1..16
vectors, partial last vectors, gaps 0..3), every result in order at the priced offset: PASS at LA/LM 4/4, 4/5, 6/6, 7/6, 7/9;
OT_S5_RED2_MUT (SUM taken as MAX) FAIL.  Kit: run_kit.sh red eq (this netlist vs original, OFF 52) / mut (constructed mutant
netlist) -- QW-S5-SCRED 10-21 rerun on Verilator 5.050 (run_kit.sh ... red eq|mut 79): witnesses results/arch/qw_slice6_1019/scred2_1020/kitbench/red79_{eq,mut}.log.

## SAFE-DESIGN checklist
1 Pins: PASS -- every input lands in one face register, every output leaves a face register (kit flow wrapper off, same
  in+1/out+1 as the old kit); rst_n 2-stage landing (qfd_dv_s5_rst2) + rc stage replicated into <= 8-load relays; census
  boundary levels 0.
2 Reach: PASS -- leaf side <= 280.8 um < 405 um; slice-scale distances are parent landings.
3 Fanout: FIXED -- bounded constructor, census 0 roots > 32 (max 24) incl. reset; kept helpers stop ABC re-sharing.
4 Depth: FIXED -- FP add LAT 7 (all cuts incl. after the sentinel LZC) / mul LAT 9, retained prefix levels: 556.8 ps / 17 lv.
5 Storage: PASS -- no runtime-indexed flop array; every delay line >= 3 deep is a kept exact-age ring, each store <= 2 kb
  (largest: chain tag line 26 b x 47 slots = 1,222 b; lane-7 operand line 32 b x 40 = 1,280 b).
6 Floorplan: no macros; one full-width std-cell band; outline from mapped area at 0.51 / 0.39 util; pins N 289 b (inputs), S
  outputs, W ck/rst_n, <= 1.5 pins/um.
7 Clock: one centre-fed root (34,272 sinks, <= 0.28 mm tile); judged on pin-flop spread <= 80 ps TT+FF; io_hold_margin 0.03.
8 Schedule: static. PRICE vs the old kit qfd_dv_s5_red: red_we / red_addr / red_data / fault +50 edges per reduction result
  ((LM-3) + 7(LA-3) + LV(LA-3) = 6 + 28 + 16); rd_v +0; busy registered; boot: ring phase reset release +2.  NOTICE to
  TOKSIM-QW2 / QW-SLICE7 (lanes/QW-SLICE7.md).

## BIND (QW-S5-SCRED 10-21)
qfd_dv_s5b_su8p2_lp.sv (5949f90af) u_red: replace module qfd_dv_s5_red by qfd_dv_s5_red2_leaf, identical ports/widths; the lp
lagref adds +50 edges on red_we/red_addr/red_data/fault (rd_v +0, busy registered). Boot: reset release +1, ring phases +2.

## QW2-SLICE2 10-21 gate fix
Gate @22a9a442d FAIL textbook.reset_landing (rst_n reached 8 async-clear flops of the RTL rst2/rc stage). Fix: kit reset_landing enable (2 plain face flops rst_n__ot_rl0 -> rl1 before the RTL landing). PRICE: reset assertion/release +2 cycles (scheduled constant); data latency unchanged.
