# hidx_score_qw4k_562_w432_c16 (L2H-IDXSCORE 2026-10-19, LEAD2-HBM; critical hb_idx_score family: gate PNGs + checklist to the coordinator, no REVIEW/submit)

Top `ot_hbm_idx_score_qw_r4s` (one-root wrapper of ot_hbm_idx_score_qw_r4), outline 43.2 x 1123.2 um, branch claude/l2h-idxscore-1019. Structural change: L2H-IDXSCORE 2026-10-19 successor of hidx_score_qw_1018 (r3 FAIL GPL-0305 at 4% util, reset_landing 4, one root over 1.12 mm, row-1 outputs one ~560 um hop from the row-0 input capture): A pin capture -> B mid stage per row -> C output pin regs (+2 edges, was +1; compiler --score-chain +1), row clocks clk_w0 / clk_w1 (die clk_engine[0/1]), landed reset ot_rst_relay_l, wf split per row, width cut to the pin-flop columns.

Benches (Verilator 5.050, fleet): qsplit_r4_pos, qsplit_r4_keyline, qsplit_r4_auxearly, qsplit_r4_rowswap; witnesses under results/rtl/hbm_idx_quarter_split_1018/{qs_r4,leaf_l}/.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- A-stage capture flop on every input, C-stage flop on every output; rst_n reaches only the 2 synchroniser flops of ot_rst_relay_l (fixed: r3 had 4 port sinks).
2 Reach: fixed -- shared inputs (query, beat control, keep bitmap) enter in row 0's face sections; r3 drove row 1's output flops one ~560 um hop from that capture. r4: A capture -> B mid stage per row -> C pin regs, every hop <= ~301 um.
3 Fanout: fixed (r4k) -- broadcast A regs feed 2 row copies (B0/B1), no register > 32 loads outside key/query bit slices. r4s gate netlist: Yosys merged the identical row copies (568 of 1,136 o_q flops; b_q/b_qv/b_kv/b_md, o_qv/o_kv, most o_aux), o_q0 driven from row 1 (~650 um, reg->out -228 ps); r4k puts each row's B+C in the non-parameterised kept module ot_hidx_qw_row (SYNTH_KEEP_MODULES) -- check the gate netlist keeps 1,136 o_q* flops.
4 Depth: PASS -- glue compares / adds only (one 20-b multiply-add for first index), all registered at B.
5 Storage: PASS -- no stores, no delay lines.
6 Floorplan: waived-with-reason -- pin-bound seam column: face length = leaf row pitch (E face ~3,330 pins per 561.6 um row ~ 5.9/um); width 43.2 um (one lattice pitch; 21.6 um gave trial GRT overflow 12,741-157,782 on M3), util ~12% (std 5.3k um2): the outline is set by the leaf row pitch and the pin faces, not by area. Aspect is inherent to a seam column that abuts 2 leaf rows.
7 Clock: fixed -- regional roots per leaf row clk_w0 / clk_w1 (die clk_engine[0/1]), pins beside each row's register mass; row-0 -> row-1 crossings reg -> reg (same PLL, fixed phase); io_hold_margin 0.03.
8 Schedule: fixed -- +2 edges on every leaf input (was +1): compiler --score-chain +1 more (score chain 11 -> 12), relative leaf timeline and reset release unchanged; handed to the die schedule (LEAD2-HBM note).
rev c: clk_w1 pin mirrored to row 1's upper W gap (rev b at row+50: clk_w1 TT/FF spread 87.9/101.9 (648), 287 (562); rst_c1 at the E-face row seam (rev a: N face, clk_w0 333.8 ps)).

ONE-ROOT variant: item 7 = one centre-fed root at the row seam (two-root r4a-c: row-1 roots 88-287 ps, row-1 domain sinks placed across the seam).
