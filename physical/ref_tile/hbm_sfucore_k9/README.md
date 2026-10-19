# hbm_sfucore_k9 -- k9s safe redesign (HBM-SAFE-K9, 2026-10-19, coordinator 0ks)

SFU core (`ot_hgi_sfu_core_split3`, WPIPE=1, GCLK=1, DRAIN_PIPE=1): 16 hardened lane leaves (`ot_su12_sfu`) on four
faces around 80 operand SRAMs (`ot_sram_1r1w_256x256_m2_r2c2`, 172.8 x 41.04, 411 M4 pins on each of the W and E faces).
Outline 1771.2 x 1900.8 (was 1598.4 x 1771.2; W +172.8 approved in 0ks, H +129.6 added here, see item 6).

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | Pins | PASS: keep_pin_regs (flop at every pin, io_flop_at_pins, OT_OFLOP_HOPS=2); reset_landing 2 stages on clk (release +2, scheduled constant) |
| 2 | Reach | PASS by construction: every lane sits <= ~300 um from its store column edge / face pins; die-face buses land in pin registers at the face. Gate confirms (no reg->reg > 405 um single-cycle) |
| 3 | Fanout | fixed (LH-SU 10-19, after the 07:38 k9s gate textbook): lane-map pass rings (460 b x 16 lanes) keep one one-hot copy per 16 bits (PASS_OHREP=16, (* keep *), was 1,381 loads per one-hot bit); the operand store's 2,048-bit sector data no longer fans to all 64 banks (WROT, item 4). WARN accepted (audit R2): reset leaves after landing (rr[0] 6,245 / rst_lg relays 2,989) -- reset is not a critical cone |
| 4 | Depth | fixed: WPIPE bank-write landing stage cuts VM meta -> bank w_mask_in (702 ps / 19 lv) and lane u_sfu -> u_output wcoll_q (717 ps / 19 lv, the 05:03 REFUSE); drain stage (k9dp) kept; LH-SU WROT: 07:38 gate textbook showed WPIPE sa_q -> bank w_addr_in 735 ps / 20 lv (per-word add + 64-way last-wins mux): each stage sector is now bank-aligned ONCE (shared rotate by addr[3:0], after WPIPE) and every bank picks among 8 slot-b words (one-hot last-wins, ~10-12 lv); same edges, same collision fault |
| 5 | Storage | PASS: all operand storage in 80 SRAM macros; no runtime-indexed flop arrays > 2 kb added |
| 6 | Floorplan | fixed: 5 group columns (col 0 = output group, 1-4 = operand groups 0-3), x 345.6/561.6/820.8/1036.8/1252.8 = 43.2 lattice; banks 0-15 at 69.12 um pitch -> 411 pins per 69.12 um of column face = 5.95 pins/um (<= 6; M6 over-macro demand 11.9/um vs 15.6/um supply); 28.08 um gaps aligned across all columns = full-width std-cell bands (no islands); channels 86.4/43.2/86.4/43.2/43.2/86.4 + 5.4 halo; aspect 1.07; hard area (lanes 1.142 + SRAM 0.567 mm2) + std 0.085 mm2 synth = 54% of 3.367 mm2. 16 per column at <= 6 pins/um needs 1,078 um of column -> H +129.6 (W alone cannot hold 80 macros at <= 6/um with lanes on four faces) |
| 7 | Clock | fixed: regional roots -- clk_st[4:0] one per store column (16 macros + bank/crossbar logic), clk = bridge + engine control, clk_pw/clk_pe pin regs, clk_lane/clk_map per lane, clk_lg per VM tap; same die clock, neighbour-matched entries; crossings flop-to-flop, judged per child pair TT/FF <= 80 ps (ot_pl_land ring fallback if a pair fails); io_hold_margin 0.03 |
| 8 | Schedule | static; +1 edge bank-write landing handed to the SFU calendar (results/rtl/hbm_safe_k9_1019/schedule.md); canonical Qswiglu lockstep shows no boundary edge moves |

## Evidence
- Benches (ot-epyc4, Verilator 5.050, @a3978bcc0): split_equiv_r23 POSITIVE PASS (edges 6679, wq_extra 1); mutants
  skip_pinreg / clkpw / nodrainpipe / gclk (clk_st[2] undriven) / wpskew (enables bypass the stage) all REJECTED;
  logs results/rtl/hbm_safe_k9_1019/bench_witness/.
- Die slot change (outline, faces, clk_st[4:0] ports) handed to H-D4G / TW5-HBM-DIE.
