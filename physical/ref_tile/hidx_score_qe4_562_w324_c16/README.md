# hidx_score_qe4_562_w324_c16 (L2H-IDXSCORE 2026-10-19, LEAD2-HBM; critical hb_idx_score family: gate PNGs + checklist to the coordinator, no REVIEW/submit)

Top `ot_hbm_idx_score_qe_r4`, outline 32.4 x 1123.2 um, branch claude/l2h-idxscore-1019. Structural change: L2H-IDXSCORE 2026-10-19 successor of hidx_score_qe_1018 (r3 FAIL: ONE root over 1.12 mm, TT/FF pin-flop spread 177.7 / 156.8 ps; reset_landing 3; util 16%): row clocks clk_e0 / clk_e1 (die clk_tail[0/1]) beside each row's E glue, per-row score registers + pins (score0 / score1, the parent re-assembles the flat 306-bit bus), keep delay as ring buffer, landed reset ot_rst_relay_l, width cut toward 40% util. Same cycles.

Benches (Verilator 5.050, fleet): qsplit_r4_pos, qsplit_r4_keyline, qsplit_r4_auxearly, qsplit_r4_rowswap; witnesses under results/rtl/hbm_idx_quarter_split_1018/{qs_r4,leaf_l}/.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- outputs score0/score1/fault are registers; inputs land in the keep ring / tail / meta input stages and the settle/online/fault registers; rst_n reaches only ot_rst_relay_l's 2 synchroniser flops (fixed: r3 had 3).
2 Reach: PASS -- each row's E glue and its score register + pins sit in that row (score split score0/score1, fixed); fault reads row 1's ev / fault reg -> reg across the row seam.
3 Fanout: PASS -- tail / meta per row, relay copy per row.
4 Depth: PASS -- E glue verbatim (r2 placed setup +100 ps).
5 Storage: fixed -- keep delay D106 x 4 b now ot_hdc_delay_rf (was a 424-flop shift chain); meta d123 x 25 b already a ring buffer (3,075 b, flop RF, 1R1W fixed pointer; waived from SRAM: the per-row store is written and read every edge at a fixed distance, no runtime index, and an SRAM macro would not fit the 32.4 um seam column).
6 Floorplan: waived-with-reason -- pin-bound seam column (W row sections face the leaf E pins); width 86.4 -> 32.4 um, util ~47% (r3 16%).
7 Clock: fixed -- regional roots per row clk_e0 / clk_e1 (die clk_tail[0/1]) beside each row's E glue (r3: one root over 1.12 mm, TT/FF spread 177.7 / 156.8 ps); io_hold_margin 0.03.
8 Schedule: PASS static; same cycles as the flat quarter's E glue.

CTS variant c16: route.cts_sink {"size": 16, "diameter_um": 20, "extra": "-sink_clustering_levels 2"}.
