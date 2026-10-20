# hidx_score_leaf_c1_648 (L2H-IDXSCORE 2026-10-19, LEAD2-HBM; critical hb_idx_score family: gate PNGs + checklist to the coordinator, no REVIEW/submit)

Top `ot_hbm_idx_score_leaf_c1`, outline 648.0 x 648.0 um, branch claude/l2h-idxscore-1019. Structural change: L2H-IDXSCORE 2026-10-19 successor of hidx_score_leaf_1017 (r10 FAIL: CTS clk_pair[0] internal-root pin-flop spread 176.2 ps, reset_landing 40, util 68%): ONE centre-fed root clk (no internal-only roots), core ot_hbm_idx_chunk_rt_l (landed relays, segmented valid-line resets, ring-buffer delays), outline 648.0 um square sized from the r10 synthesis area 209,848 um2 (~50% util); same data ports and cycles.

Benches (Verilator 5.050, fleet): chunk_rt_l_pos, chunk_rt_l_gap4, chunk_rt_l_qlate1, chunk_rt_l_seam, chunk_rt_l_swap; witnesses under results/rtl/hbm_idx_quarter_split_1018/{qs_r4,leaf_l}/.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every W input lands in pin regs f_*/hb_p/b_w, every E output launches from g_*/e_bus (RTL); reset: rst_n reaches only the 2 synchroniser flops of ot_rst_relay_l (fixed: r10 had 40 port sinks incl. rdy1/rdy2/online; those now clear from the landed copy, equivalent because prdy is 0 until the regions release).
2 Reach: PASS -- W pin reg -> E pin reg hop = half a leaf + channel (<= ~364 um); all other hops are inside the leaf, register to register.
3 Fanout: fixed -- valid line u_vl (520 reset clears on one relay copy) split into 13 segments with own kept relay copies; region relays drive one adder each (~410 flops, reset WARN tier only, < 8000 refuse; reset nets are not data cones). Kept copies are (* keep *) relay registers (ot_keep_regs hook).
4 Depth: PASS -- r10 textbook depth 553.4 ps (<= 600 ps); ring-buffer reads add a log2(N) mux level before an output register.
5 Storage: fixed -- unreset delay lines >= 3 deep (term u_td up to 63 x 17 b, block partials u_bd 7/14 x 33 b, seed u_sd 7 x 33 b) are ot_hdc_delay_rf ring buffers (cycle-exact); no store > 2 kb (query store per head 560 b, not runtime-indexed). Waived: 1-bit fault delays (<= 7 deep, 1 bit) and the 5-bit reset valid line (reset contents are part of the protocol).
6 Floorplan: PASS -- outline 648.0 x 648.0 um from the r10 synthesis area 209,848 um2 (50% util); no macros; square; full std-cell band.
7 Clock: fixed -- ONE centre-fed root clk (N-face centre pin), no internal-only roots (r10: clk_pair[0] internal root spread 176.2 ps); io_hold_margin 0.03.
8 Schedule: PASS static; same cycles as hidx_score_leaf_1017 (chunk_rt_l bench vs the systolic chunk).
