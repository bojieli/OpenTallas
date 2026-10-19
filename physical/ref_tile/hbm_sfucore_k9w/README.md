# hbm_sfucore_k9w -- k9r RTL on a re-spaced store floorplan (LEAD2-HBM/L2H-SU, 2026-10-19)

Why: both k9s2 (gate ep4 hbm_sfucore_k9-20261019-120005) and k9r (hbm_sfucore_k9r-20261019-123227) hit GATE_STALL at the 14,400 s
step cap inside placement: GPL 3h45m / 2h04m (3,503 routability iterations, final weighted congestion 1.078, timing-driven worst slack
-17 ns), repair_design +58k buffers on 39k long wires. The floorplan has the same defect as the GQ issue tile: each
ot_sram_1r1w_256x256 carries 411 M4 pins on each 41.04 um W/E face (10 pins/um) and the 5 store columns stood 43.2 um apart
(32 um beyond the 5.4 um halos), so two 10 pins/um faces + their bank logic shared every inner channel.

Change (geometry only, RTL/kit flow = k9r @885a26d05 incl. OT_RST_COPIES_SDFF): store columns at x = 345.6 / 604.8 / 864.0 /
1123.2 / 1382.4 (86.4 um apart, 75.6 um beyond the halos), rows unchanged; E lanes 1512 -> 1641.6, N/S lanes 345.6 / 691.2 /
993.6 / 1339.2; outline 1771.2 x 1900.8 -> 1900.8 x 1900.8 (die slot +129.6 um W-E -> H-D4G). Gate step cap raised to 8 h for
this 1.9 mm, 96-macro tile (runtime only). Parallel to k9r; bind the first to close, cancel the other.
Item 6 below is superseded by: FIXED -- 43.2 lattice kept, inner pin-face channels 75.6 um, square outline.

---- k9r README (inherited) ----
# hbm_sfucore_k9r -- k9s3: k9s2 + registered reset distribution trees with kept copies (LH-K9R, 2026-10-19)

Parallel variant of hbm_sfucore_k9 (k9s2, same commit base 5c81e31f0): identical outline, macros, pins, clocks; only RST_TREE=1 + the
reset copy split differ. Bind whichever of k9 (k9s2) / k9r (k9s3) closes first under this checklist; cancel the other.

SFU core (`ot_hgi_sfu_core_split3`, WPIPE=1, GCLK=1, DRAIN_PIPE=1, WROT=1, PASS_OHREP=16, RST_TREE=1): 16 hardened lane leaves (`ot_su12_sfu`) on four
faces around 80 operand SRAMs (`ot_sram_1r1w_256x256_m2_r2c2`, 172.8 x 41.04, 411 M4 pins on each of the W and E faces).
Outline 1771.2 x 1900.8 (was 1598.4 x 1771.2; W +172.8 approved in 0ks, H +129.6 added here, see item 6).

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | Pins | PASS: keep_pin_regs (flop at every pin, io_flop_at_pins, OT_OFLOP_HOPS=2); every reset pin (rst_n, rst_lg_n[3:0], rst_map_n[15:0], rst_lane_n[15:0]) lands in 2 registered stages at the face on clk (reset_landing; each landing flop drives one load: rl0 -> rl1 -> the tree's level A) |
| 2 | Reach | PASS by construction: every lane sits <= ~300 um from its store column edge / face pins; die-face buses land in pin registers at the face. Gate confirms (no reg->reg > 405 um single-cycle) |
| 3 | Fanout | fixed: (a) lane-map pass rings keep one one-hot copy per 16 bits (PASS_OHREP=16, was 1,381 loads); WROT removes the 2,048-bit x 64-bank sector fan-out (item 4). (b) LH-K9R: reset. k9s census (07:38 gate 1_2_yosys.v, textbook hf_report 32): rr[0] 6,245, rr[1] 1,059, rst_lg_n__ot_rl1[k] 2,989 x 4 mapped loads. Now every landed reset feeds a registered 2-level tree of KEPT identical copies on its consumers' root (rtl/lib/ot_rst_kept_tree.sv: rst_n 16 -> 384, rst_lg_n[k] 8 -> 160, rst_map_n[j] 1 -> 8, rst_lane_n[j] 1 -> 1); spec reset_relay_split (max 32, family u_fl_rst_*.ra/rb) re-points the loads over the copies after OT_RST_COPIES_SDFF folds the synchronous resets into $sdff SRST ports, so one coarse load = one mapped gate (fleet yosys proof: 520 sync-reset bits over 24 copies -> mapped 22 max). Verification on the gate's mapped netlist: ot_rst_copies.tsv (every family OK) + textbook_lint --set hf_report=32 (no reset driver > 32); flat synthesis keeps the copies (ot_keep_regs keep cells; names u_ot_pr_core.u_core.g_rt.u_fl_rst_*) |
| 4 | Depth | fixed: WPIPE bank-write landing stage cuts VM meta -> bank w_mask_in (702 ps / 19 lv) and lane u_sfu -> u_output wcoll_q (717 ps / 19 lv, the 05:03 REFUSE); drain stage (k9dp) kept; LH-SU WROT: 07:38 gate textbook showed WPIPE sa_q -> bank w_addr_in 735 ps / 20 lv (per-word add + 64-way last-wins mux): each stage sector is now bank-aligned ONCE (shared rotate by addr[3:0], after WPIPE) and every bank picks among 8 slot-b words (one-hot last-wins, ~10-12 lv); same edges, same collision fault |
| 5 | Storage | PASS: all operand storage in 80 SRAM macros; no runtime-indexed flop arrays > 2 kb added |
| 6 | Floorplan | fixed: 5 group columns (col 0 = output group, 1-4 = operand groups 0-3), x 345.6/561.6/820.8/1036.8/1252.8 = 43.2 lattice; banks 0-15 at 69.12 um pitch -> 411 pins per 69.12 um of column face = 5.95 pins/um (<= 6; M6 over-macro demand 11.9/um vs 15.6/um supply); 28.08 um gaps aligned across all columns = full-width std-cell bands (no islands); channels 86.4/43.2/86.4/43.2/43.2/86.4 + 5.4 halo; aspect 1.07; hard area (lanes 1.142 + SRAM 0.567 mm2) + std 0.085 mm2 synth = 54% of 3.367 mm2. 16 per column at <= 6 pins/um needs 1,078 um of column -> H +129.6 (W alone cannot hold 80 macros at <= 6/um with lanes on four faces) |
| 7 | Clock | fixed: regional roots -- clk_st[4:0] one per store column (16 macros + bank/crossbar logic), clk = bridge + engine control, clk_pw/clk_pe pin regs, clk_lane/clk_map per lane, clk_lg per VM tap; same die clock, neighbour-matched entries; crossings flop-to-flop, judged per child pair TT/FF <= 80 ps (ot_pl_land ring fallback if a pair fails); io_hold_margin 0.03 |
| 8 | Schedule | static; +1 edge bank-write landing (results/rtl/hbm_safe_k9_1019/schedule.md); LH-K9R reset trees: every reset releases 4 edges after the die (rst_n -1, lg/map/lane +2), one-time constant handed to the die reset sequencer (results/rtl/hbm_safe_k9r_1019/schedule.md), 0 edges per token |

## Evidence
- Benches (ot-epyc4, Verilator 5.050, @a3978bcc0): split_equiv_r23 POSITIVE PASS (edges 6679, wq_extra 1); mutants
  skip_pinreg / clkpw / nodrainpipe / gclk (clk_st[2] undriven) / wpskew (enables bypass the stage) all REJECTED;
  logs results/rtl/hbm_safe_k9_1019/bench_witness/.
- Die slot change (outline, faces, clk_st[4:0] ports) handed to H-D4G / TW5-HBM-DIE.
- k9s3 (LH-K9R): benches + mutants (incl. rsttree: lg path 1 tree never releases) on ot-epyc5 Verilator 5.050; logs
  results/rtl/hbm_safe_k9r_1019/bench_witness/. Gate: --cts --remote auto (see Gate section once collected).
