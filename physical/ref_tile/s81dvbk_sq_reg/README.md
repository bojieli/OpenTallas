# s81dvbk_sq_reg -- TOPK selector quarter, FAN32 RTL + REGIONAL clock roots (dsdv_bksel_q, LEAD2-S81/TOPK2 2026-10-19)

PARALLEL structural clock variant of s81dvbk_sq_succ2 / succ2c (same FAN32 RTL d58faf9b0, same geometry 324 x 540,
16 p192 macros on the 43.2 lattice: line pool 6x at y 43-284, OFQ 5x W / FQ 5x E at y 285-485, full-width top band,
N pins <= 5.6/um, t_o W full face, ck N centre). succ2/succ2c only change CTS options; this kit changes the clock
STRUCTURE.

Why (measured, results/arch/s81_topk_reg_1019/succb_cts_flop_spread.txt): per-flop CTS replay of succb 4_1_cts.odb
shows the single 12-level tree over 40.5k sinks is BIMODAL, not noisy: band + upper-stack masses (u_ps, u_hf, FQ/OFQ,
status/IO) at 522-560 ps TT, while the line-pool / ingest masses (u_pi 563-656, pi_line, i1_p 585-632, half of u_hc,
g_m2 up to 656) hang on one late branch (+70..+100 ps). All-flop spread 158.6 TT / 138.1 FF.

Change: pre_cts_extra physical/common_flow/clock_split_km.tcl, OT_CKKM_K 16, OT_CKKM_PORT ck. The ck port net is split
into 16 compact sink clusters (k-means on placed sinks, ~2.5k sinks / ~80 x 135 um each); one BUFx24 local root sits at
each cluster centroid, i.e. beside its register mass next to its SRAM stack; TritonCTS builds one short tree per region
and balances the 16 region roots under one top tree from the N-face pin. Same port, clock, flops, SDC, cycles.

Region crossings: every crossing is an existing register-to-register path on the one phase-0 tile port, timed by
ordinary STA at TT and FF (setup + hold, boundary hold margin 0.03). The tile is 324 x 540 um, so every crossing is
< 405 um and within one cycle; a 4-slot landing ring (LANDING-CONTRACT, for die links / parents > ~1 mm) is not needed
here. Added edges: 0 (nothing for the INBOX pricer).

Safe-design checklist (owner 10-19):
1. Pins: PASS. Source-registered QIO pin flops (pin_regs off with reason, as succ2) + io_flop_at_pins; reset_landing 2 stages.
2. Reach: PASS by construction (farthest macro capture -> band ~300 um < 405); checked at gate placement.
3. Fanout: FIXED (FAN32, as succ2): all >256-load selector control nets are KEPT copies (<= 50 loads); gate synthesis must
   show g_clc/g_gsc/g_frc/g_sl copies distinct.
4. Depth: PASS (as succ2): group select 4->16 decode + 16-way AND-OR between registers; no new arbitration.
5. Storage: PASS: FQ/OFQ in 10 SRAM, line pool in 6 SRAM; hbin counters are per-bin, not runtime-indexed.
6. Floorplan: PASS as s81dvbk_sq_succ (lattice, halos, band); fill WAIVED-with-reason (~33 % std fill, macro/pin-escape bound).
7. Clock: FIXED structurally: 16 regional roots at the register-mass centroids (clock beside its mass), balanced top tree;
   io_hold_margin 0.03; regional reset copies (RST64, <= 256 loads). Gate must show TT/FF pin-flop spread <= 80 ps.
8. Schedule: PASS. Static; 0 added cycles (clock-tree change only; FAN32 0 edges; INDEXED13 1037 reserved cycles priced).

Benches: identical RTL/defines to s81dvbk_sq_succ2 (Verilator 5.050, results/arch/s81_topk_fan32_1019): legacy / indexed13 /
ties / ninf / zeros PASS; identity / corrupt / early FAIL; MUT_GS FAIL 70, MUT_CLR FAIL 74 (committed witnesses).
Review: dsdv_bksel_q has > 1 failed route -> COORD-REVIEW-QUEUE entry [LEAD2-S81/TOPK2], no REVIEW.json, no submit by the lane.
