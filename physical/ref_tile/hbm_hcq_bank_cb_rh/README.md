# hbm_hcq_bank_cb_rh (HBM-HC7-BANK 10-20, H.STA.BLK.17) -- PARALLEL FALLBACK
Top ot_hbm_hc_bankq_rh_static (rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankrc_static.sv), successor of hbm_hcq_bank_cb_rc3.
Why: cb_rc3 --cts gate 10-20: glue root clk TT pin-flop spread 354.9 ps (2,398 boundary of 5,221 sinks, avg sink wire 1,301 um, depth 15..17); cb_rc (1 root, all pin flops anchored) 131.1 ps (4,476 of 10,789).  The rc3 placement (3_place.odb) shows every 2,048-bit group row-local (CPI sums beside their own leaves
x 350..632, SRAM capture / lane enables beside their row, CPO sums between the row and the out face, landing in the W-S
corner); one glue root per face spanned the whole 777.6 x 734.4 tile around 12 SRAMs.
Generator: tools/ref_tile/specs_hbm_b_rtl2_1017/hc7bank_rr.py.
## Clock partition (half-tile (rows 0-1 / rows 2-3) regional glue roots, 7 CTS roots + 20 hard entries)
clk, clk_c, clk_o, clk_r0, clk_r1, clk_q0, clk_q1: clk = in-face landing / write port / reset relays / CPI scalars; clk_c = stage control; clk_o = CPO
scalars; clk_r<r> = CPI sums + SRAM read capture + lane enables of its rows; clk_q<r> = CPO sums of its rows.
Hard entries ck_l[7:0] (lane leaves), ck_w[7:0] / ck_x[3:0] (raw-Liberty SRAM clocks) unchanged.  Cross-root paths are
same-source, in-tile (< 1 mm) and STA-timed; the clock rule is evaluated per root (pin-flop spread <= 80 TT / FF).
## SAFE-DESIGN checklist
1 Pins: every input lands in an RTL flop, every output is a flop; landing / control scalar pin flops (xb_d, wv, xv, j, wa, wfault, d_*, o_*) ANCHORED at their faces (io_flop_at_pins + OT_OFLOP_PORT_RE); reset lands in 2 clk stages, then RTL ot_rst_relay copies. PASS
2 Reach: 2,048-bit chain flops NOT anchored (anchored: W face -> col-1 leaf ~605 um, row-3 leaf -> out face ~562 um single-cycle hops); the placer splits face -> flop -> leaf; write port 43 um from the in face. PASS (gate / post-GRT reach check measures)
3 Fanout: pre-gate native census, mapped netlist on actual Liberty (leaf .lib + SRAM .lib): PASS, 0 > 32, max 32, 20,124 roots (ot-epyc5 /srv/opentallas-scratch2/claude/hc7bank/census_rh_cb.json); FAN32 kept copies as rc3. PASS
4 Depth: datapath unchanged (cb_s1 gate depth 178 ps). PASS
5 Storage: weights / x in SRAM macros (8 x 1024x256, 4 x 128x256). PASS
6 Floorplan: = rc3 kit (x SRAM MY x43.2, weight pair MY x172.8, leaves x432 / x604.8); macros on the 43.2 lattice; outline 777.6 x 734.4, aspect 1.06. PASS
7 Clock: half-tile (rows 0-1 / rows 2-3) regional glue roots (each one compact region) + per-child / per-SRAM entries; io_hold_margin 0.03. FIXED (gate measures)
8 Schedule: static; 0 added edges (ring lockstep Verilator 5.050 +define+HC_BANK_RC +define+HC_BANK_RH: results/rtl/hbm_hc_ring_1020_bankrc/ring_rh_*.log). PASS
Die contract: pin faces / ranges unchanged (HCRING joint plan); clock entry ports clk, clk_c, clk_o, clk_r0, clk_r1, clk_q0, clk_q1 + ck_l / ck_w / ck_x -> the die clock forest delivers each at phi - R (H-D4G / HBM-DIE6).
