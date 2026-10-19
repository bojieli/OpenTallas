// fc_xr2 (HF-5a 2026-10-18): the 2-stage successor of ot_hbm_accel_smh_fc_xr (rtl/hbm_accel/sm/ot_hbm_accel_smh.sv).
// Same ports, pin plan (results/arch/hbm_native_1013/sm/physical_specs/smn_fcxr_ref_fa_pins.tcl) and function, one
// register stage more on every path: stage A at the input faces (xi N, li / fi E-top), stage B at the output faces
// (xo S, lo / fo E-bottom), so the 151 um face-to-face wire is a reg->reg path inside the tile.
// Why (native audit results/arch/hf5_1018/native, record 1e78e63ef): the one-stage fc_xr anchors its single flop at the
// input pin (DEF: u_xd y 141-149 of 151, u_ld at li), so every xo / lo launch carries the whole tile: 409 ps on 2,642 pins
// (budget 220).  A one-stage relay across 151 um cannot meet launch 220 + capture 190 with hold pads at both faces.
// Latency: xo, lo and fo are +1 cycle against fc_xr, all three equally, so fc_b's xi stays aligned with its li / fi.
// The +1 reaches front_c's rout_*2, bout_*1 and r3a (-> fc_bc fo_row3): see lanes/HF-5.md "HF-5a" for the calendar.
// OT_SMH_FC_XR2_MUT_X1 / _MUT_L1 (bench mutants only): bypass stage B on xo / lo.
module ot_hbm_accel_smh_fc_xr2 #(parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [2068:0] xi, output wire [2068:0] xo,
    input  wire [554+TAGW-1:0] li, output wire [554+TAGW-1:0] lo,
    input  wire [2:0]    fi, output wire [2:0]    fo
);
    localparam integer LW = 554 + TAGW;
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rn));
    wire [2068:0] xa, xb;
    wire [LW-1:0] la, lb;
    wire [2:0]    fa;
    // stage A (input faces)
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_xav (.clk(clk), .rst_n(rn), .en(1'b1), .d(xi[2068]), .q(xa[2068]));
    ot_hbm_accel_smh_kreg #(.W(2068)) u_xad (.clk(clk), .rst_n(rn), .en(1'b1), .d(xi[2067:0]), .q(xa[2067:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_lav (.clk(clk), .rst_n(rn), .en(1'b1), .d(li[LW-1 -: 3]), .q(la[LW-1 -: 3]));
    ot_hbm_accel_smh_kreg #(.W(LW-3)) u_lad (.clk(clk), .rst_n(rn), .en(1'b1), .d(li[LW-4:0]), .q(la[LW-4:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_fa (.clk(clk), .rst_n(rn), .en(1'b1), .d(fi), .q(fa));
    // stage B (output faces)
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_xbv (.clk(clk), .rst_n(rn), .en(1'b1), .d(xa[2068]), .q(xb[2068]));
    ot_hbm_accel_smh_kreg #(.W(2068)) u_xbd (.clk(clk), .rst_n(rn), .en(1'b1), .d(xa[2067:0]), .q(xb[2067:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_lbv (.clk(clk), .rst_n(rn), .en(1'b1), .d(la[LW-1 -: 3]), .q(lb[LW-1 -: 3]));
    ot_hbm_accel_smh_kreg #(.W(LW-3)) u_lbd (.clk(clk), .rst_n(rn), .en(1'b1), .d(la[LW-4:0]), .q(lb[LW-4:0]));
    ot_hbm_accel_smh_kreg #(.W(3), .RST(1)) u_fb (.clk(clk), .rst_n(rn), .en(1'b1), .d(fa), .q(fo));
`ifdef OT_SMH_FC_XR2_MUT_X1
    assign xo = xa;
`else
    assign xo = xb;
`endif
`ifdef OT_SMH_FC_XR2_MUT_L1
    assign lo = la;
`else
    assign lo = lb;
`endif
endmodule
