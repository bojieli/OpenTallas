# hbm_hcq_bank_e2_rl (HBM-HCBANK9 10-20, H.STA.BLK.17 edge bank e2)
Top ot_hbm_hc_bankq_ft_rl_static (rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankrc_static.sv). Generator tools/ref_tile/specs_hbm_b_rtl2_1017/hc9bank_e2.py.
Base hbm_hcq_bank_e2_1017 (single clk; its route ring1-47247cc08 was cancelled in a GRT hang 10-19). Pattern = b0/cb _rl (hc9bank_rl.py: one clock root per compact pin-anchored register mass).
## Clock partition (15 glue CTS roots + 20 hard entries ck_l / ck_w / ck_x)
clk, clk_a, clk_c, clk_w0, clk_w1, clk_w2, clk_w3, clk_x0, clk_x1, clk_x2, clk_x3, clk_e0, clk_e1, clk_e2, clk_e3. clk = S-face landing / write scalars / feed registers / reset relays; clk_a = write mass; clk_c = stage control;
clk_w<r> / clk_x<r> = SRAM read capture anchored beside rd_out; clk_e<r> = lane enables (row-local, unanchored). No CPI / CPO on the edge bank (unchanged).
Weight SRAMs MY (rd_out faces the lanes at x 259.2; e2_1017 R0 faced the W tile edge); x SRAMs R0 (rd_out faces W, toward the lanes). Root pins N face.
## SAFE-DESIGN checklist
1 Pins: as e2_1017 (RTL landing / feed / write flops; chain pins unregistered on the edge bank, die-schedule unchanged); reset 2 clk stages at the S face. PASS (unchanged)
2 Reach: capture beside rd_out -> leaf w_i ~40-360 um, x capture -> leaf x_i ~30-340 um. PASS (gate / route measure)
3 Fanout: native census mapped netlist PASS, max 32 (ot-epyc5 /srv/opentallas-scratch2/claude/hcbank9/census_rl_e2.json). PASS
4 Depth: datapath unchanged. PASS
5 Storage: SRAM macros (8 x 1024x256, 4 x 128x256). PASS
6 Floorplan: e2_1017 positions (43.2 lattice), 734.4 sq die slot; weight SRAM orientation MY. PASS
7 Clock: one root per compact anchored mass; io_hold_margin 0.03. FIXED (gate measures every root <= 80 TT / FF)
8 Schedule: static, 0 added edges (ring lockstep +define+HC_BANK_RC +define+HC_BANK_RL: results/rtl/hbm_hc_ring_1020_bankrl/ring_rl_*.log). PASS
Die contract: chain / write / feed pins unchanged; clock entry ports added -> die forest delivers each at phi - R (NOTICE lanes/HBM-DIE13.md).
