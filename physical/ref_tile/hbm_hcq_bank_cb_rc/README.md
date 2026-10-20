# hbm_hcq_bank_cb_rc (HBM-HCBANK6 10-20, H.STA.BLK.17)
Top ot_hbm_hc_bankq_rc_static (rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankrc_static.sv), regional-clock successor of the cb_s1 / b0_s1 SAFE kits.
Why: cb_s1 --cts gate (10-19) GATE_STALL in post-GRT hold repair: one balanced clk SPINE (15,636 buffers) over 10,737 sinks
(8 hard lane leaves + 12 SRAM clock pins + 10.7 k glue flops), TT insertion 975..1271 ps (296 ps spread across the
glue/leaf/SRAM boundary); reg->macro -129.5 (wa_q -> x SRAM 600 um); macro->reg -12.9 (row-3 leaf y -> S-face flop); weight
SRAM rd_out faces (R0 = macro W face) pointed away from the lanes.  Generator: tools/ref_tile/specs_hbm_b_rtl2_1017/hcbank6_rc.py.
## SAFE-DESIGN checklist
1 Pins: every input lands in an RTL flop, every output is a flop (CPI/CPO chain pin registers, beat/write pin flops); reset_landing 2 clk stages, then RTL ot_rst_relay copies. PASS
2 Reach: write port 43 um from the in face (x SRAM moved from x648); chain pin flops anchored at the faces (cb_s1 convention, io_flop_at_pins cols 4). FIXED
3 Fanout: MAPPED native32 census (actual Liberty, leaf .lib + SRAM .lib) census_rc_cb: 0 > 32 (max 32, 20,121 roots; 10,787 flops); base bankq netlist was 4 drivers > 32 (beat-slot hold enables 3 x 512, stage ss select 64) -> 16 kept beat-pin copies, 4 kept lane-enable source copies. FIXED
4 Depth: unchanged datapath (cb_s1 gate depth 178 ps). PASS
5 Storage: weights / x in SRAM macros (8 x 1024x256, 4 x 128x256). PASS
6 Floorplan: as cb_rc3; macros on the 43.2 lattice; SRAM dense pin faces (rd_out / address, ~5.9 pins/um intrinsic) face the 84.5 um lane channel, never a lane face across < 34 um; channels >= 31.8 um; outline 777.6 x 734.4 (cb_s1 slot request), aspect 1.06. FIXED
7 Clock: hybrid_entries cluster, CTS roots clk (one glue root, FALLBACK of cb_rc3); ck_l[g] per hard lane leaf (insertion.json 180.6 TT), raw-Liberty ck_w[g] / ck_x[h] per SRAM: the die delivers phi - R at every entry (no spine, no 300 ps all-sink spread); io_hold_margin 0.03. FIXED (gate measures)
8 Schedule: static; 0 added edges (ring lockstep Verilator 5.050 HC_BANK_RC: see results/rtl/hbm_hc_ring_1020_bankrc). PASS
Die contract: pin faces/ranges unchanged (HCRING joint plan); NEW clock entry ports (clk, ck_l[7:0], ck_w[7:0], ck_x[3:0]) on ANY face -> die clock forest must deliver them (H-D4G / HBM-DIE6).
