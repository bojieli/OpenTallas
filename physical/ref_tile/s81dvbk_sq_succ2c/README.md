# s81dvbk_sq_succ2c -- TOPK selector quarter FAN32 (dsdv_bksel_q, LEAD2-S81/TOPK 2026-10-19)

Successor of s81dvbk_sq_succ (88450eee4) / s81dvbk_sq_succb (07fb519c3). Same geometry as s81dvbk_sq_succ (324 x 540,
16 p192 macros on the 43.2 lattice in two abutted W/E-pin stacks, rd faces into the centre channel, full-width top band,
N pins <= 5.6/um, t_o W full face, ck N centre). Opt-in defines: successor set + OT_S81PH_SEL_FAN32. Default RTL unchanged.

Why (measured): succ gate 113938 (ep7) GATE_CTS_RC=137 = the gate's 14400 s stage timeout (GATE_STALL), NOT OOM (no
openroad OOM on ep7 in that window): post-CTS repair_timing ran >10,500 iterations on 507 setup endpoints (WNS -116.6 ->
-85.6 ps, TNS ~-10.3 ns) after placement met +39.9 ps; GPL routability never converged (weighted congestion 1.28-1.33,
~40 % of GCells overflowed). Clock: one 12-level H-tree, 40,494 register sinks, boundary arrival 430..533 ps (succ) and
TT/FF all-flop spread 158.6/138.1 ps (succb 114414). Textbook: 8 control nets > 1,400 loads in the native selector slice
(hist clear 2820, group select r_cg/r_fg 2816, hist update v2 2112/2129, packer shift qf 1600, sh 1413).

Change (exact, 0 added edges; every copy is a (* keep *) register on the original's edge):
- histogram bin clear + update enable: 128 copies each per histogram, 2 bins (22 flops) per copy;
- group select gbin <= hbin[16*CB*gsel +: 16*CB] -> 16 copies of r_cg / r_fg (one per output bin), decoded constant-
  index one-hot AND-OR (no runtime part-select / yosys SHARE);
- packer rotate shift amounts: one copy per output lane (32 lanes x 4 bits, RE = 50 selects each), stage 0 from frun's
  next value, later stages forwarded on qf's edge; last-stage copies omitted (no dead kept flops).
Cost: about +1.9k flops per quarter (~4.7 % of 40.5k).
Clock: PARALLEL variant: route.cts_sink sink_clustering false + -no_obstruction_aware (unclustered H-tree; qkd_d2d_static 10-15 sparse macro tile all flops 442..508 ps).

Safe-design checklist (owner 10-19):
1. Pins: PASS. Source-registered QIO pin flops + io_flop_at_pins; reset_landing 2 stages.
2. Reach: PASS by construction (farthest macro capture -> band ~300 um < 405); confirmed at gate placement.
3. Fanout: FIXED. All >256-load selector control nets replaced by KEPT copies (<= 50 loads; clr/v2 22, gsel decode
   <= 16 x 11, shift 50); successor copies kept (b1c 3, oh 37 pairs, FIFO forwarding 74/76, INDEXED13 format 27).
   Gate synthesis must show the copies distinct (paramod names: check g_clc/g_gsc/g_frc/g_sl counts in the netlist).
4. Depth: PASS. Group select is a 4->16 decode + 16-way AND-OR (~5 levels) between registers; no new arbitration.
5. Storage: PASS (successor): FQ/OFQ in 10 SRAM, line pool in 6 SRAM; hbin counters are runtime-updated per bin (not indexed).
6. Floorplan: PASS as s81dvbk_sq_succ (lattice, halos, band); fill WAIVED-with-reason (~33 % std fill, macro/pin-escape bound).
7. Clock: FIXED (provision) - PARALLEL variant: route.cts_sink sink_clustering false + -no_obstruction_aware (unclustered H-tree; qkd_d2d_static 10-15 sparse macro tile all flops 442..508 ps); regional reset copies (RST64 <= 256 loads); io_hold_margin 0.03.
   Gate must show TT/FF pin-flop spread <= 80 ps.
8. Schedule: PASS. Static; FAN32 adds 0 cycles (bench below); INDEXED13 1037 reserved cycles already priced (S81.TOPK_FINAL).

Benches (Verilator 5.050, results/arch/s81_topk_fan32_1019/run_suite.sh): legacy / indexed13 / ties / ninf / zeros PASS;
identity / corrupt / early FAIL; FAN32 group-select mutant (all gsel copies ^1, OT_S81PH_SEL_FAN32_MUT_GS) FAIL 70 mism and clear-copy mutant (lower-half clear copies stuck, OT_S81PH_SEL_FAN32_MUT_CLR) FAIL 74 mism (witnesses bench/mut_gs, bench/mut_clr). evidence/suite_positive.log = first run (positives PASS; its single-bin gsel mutant was too weak and undetected, replaced).
