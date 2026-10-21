# hbm_hcq_bank_b0_rm (HBM-HCBANK9 10-20, H.STA.BLK.17)
Top ot_hbm_hc_bankq0_rm_static (rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankrc_static.sv), params {'CPO': 1, 'DRLY': 2}. Generator tools/ref_tile/specs_hbm_b_rtl2_1017/hc9bank_rl.py.
Successor of hbm_hcq_bank_b0_rp (--cts gate FAIL 10-20: clk_r0 pin-flop spread 150.2 ps TT, 800 internal sinks in 3 separated clusters).
Evidence: 3_place.odb sink dump per root (b0_rp: wd x361-429 / xd x235-425 / lane enables x39-212 on clk_r0; clk_q0 CPO sums y150-700; cb_rw: clk pin flops x3-8 + hold/asm_q/wd_q x307-773).
## Clock partition (17 glue CTS roots + 20 hard entries ck_l / ck_w / ck_x)
clk, clk_c, clk_o, clk_r0, clk_r1, clk_r2, clk_r3, clk_e0, clk_e1, clk_e2, clk_e3, clk_q0, clk_q1, clk_q2, clk_q3, clk_s0, clk_s1.
clk = in-face pin flops + reset relays + write mass; clk_c = stage control; clk_o = CPO scalars;
clk_r<r> = wd + xd capture of SRAM row r, anchored beside rd_out (io_flop_at_pins macro_out_pins rd_out);
clk_e<r> = lane enables beside the leaf lv_i / ss_i pins (macro_pins); clk_q<r> = CPO sums beside the leaf y face (macro_out_pins y); clk_s0 / clk_s1 = exit relay.
Cross-root paths: same-source in-tile entries (die delivers phi - R), STA-timed, as the _rr kits. 0 added edges.
## SAFE-DESIGN checklist
1 Pins: every input lands in an RTL flop, every output is a flop; scalar pin flops anchored at their faces; reset lands in 2 clk stages, then RTL ot_rst_relay copies. PASS
2 Reach: SRAM capture anchored at rd_out (SRAM clk->q budget); capture -> leaf w_i / x_i up to ~400 / ~580 um single-cycle from a std flop; CPO flop (beside leaf y) -> out face up to ~560 um. WAIVED (09:35 freeze: guidance; repeated reach measured 600-750 um; route STA decides). Replaces the e0_1017 failure mode (leaf 347 ps clk->y arc + >500 um wire).
3 Fanout: pre-gate native census on the mapped netlist (ot-epyc5 /srv/opentallas-scratch2/claude/hcbank9/census_rm_b0.json): PASS, 0 drivers > 32, max 32. PASS
4 Depth: datapath unchanged (gate depth 170 ps). PASS
5 Storage: weights / x in SRAM macros (8 x 1024x256, 4 x 128x256). PASS
6 Floorplan: b0 geometry (= b0_rp); macros on the 43.2 lattice; outline 777.6 x 734.4, aspect 1.06. PASS
7 Clock: one root per compact anchored register mass, root pins on the free W face at the row line; io_hold_margin 0.03. FIXED (gate measures every root <= 80 TT / FF)
8 Schedule: static; 0 added edges (ring lockstep Verilator 5.050 +define+HC_BANK_RC +define+HC_BANK_RM: results/rtl/hbm_hc_ring_1020_bankrl/ring_rm_*.log). PASS
Die contract: chain / write pin faces and ranges unchanged; clock entry ports change (clk, clk_c, clk_o, clk_r0, clk_r1, clk_r2, clk_r3, clk_e0, clk_e1, clk_e2, clk_e3, clk_q0, clk_q1, clk_q2, clk_q3, clk_s0, clk_s1) -> die clock forest delivers each at phi - R (NOTICE lanes/HBM-DIE13.md).
