// tools/hbm_hub_quarter_gen.py --hub: hardened composition of hfd_hc (hub + die head relays + 88 tiles)
`timescale 1ns/1ps
module hfd_hc (
    input  wire [0:0] ck0e,
    input  wire [0:0] ck0w,
    input  wire [0:0] ck1e,
    input  wire [0:0] ck1w,
    input  wire [0:0] ck2e,
    input  wire [0:0] ck2w,
    input  wire [0:0] ck3e,
    input  wire [0:0] ck3w,
    input  wire [0:0] ck4e,
    input  wire [0:0] ck4w,
    input  wire [0:0] ck5e,
    input  wire [0:0] ck5w,
    input  wire [0:0] ck6e,
    input  wire [0:0] ck6w,
    input  wire [0:0] ck7e,
    input  wire [0:0] ck7w,
    input  wire [1023:0] f_sfu,
    input  wire [0:0] rst,
    output wire [1023:0] t_sfu
);
    wire clk0e = ck0e[0];
    wire clk0w = ck0w[0];
    wire clk1e = ck1e[0];
    wire clk1w = ck1w[0];
    wire clk2e = ck2e[0];
    wire clk2w = ck2w[0];
    wire clk3e = ck3e[0];
    wire clk3w = ck3w[0];
    wire clk4e = ck4e[0];
    wire clk4w = ck4w[0];
    wire clk5e = ck5e[0];
    wire clk5w = ck5w[0];
    wire clk6e = ck6e[0];
    wire clk6w = ck6w[0];
    wire clk7e = ck7e[0];
    wire clk7w = ck7w[0];
    wire [161:0] hbo_0; wire [255:0] hqo_0;
    wire [161:0] hbo_1; wire [255:0] hqo_1;
    wire [161:0] hbo_2; wire [255:0] hqo_2;
    wire [161:0] hbo_3; wire [255:0] hqo_3;
    hfd_hc_hub u_hub (.clk(clk4e), .rst(rst[0]), .f_sfu(f_sfu), .t_sfu(t_sfu), .hb0(hbo_0), .hb1(hbo_1), .hb2(hbo_2), .hb3(hbo_3), .hq0(hqo_0), .hq1(hqo_1), .hq2(hqo_2), .hq3(hqo_3));
wire [161:0] tb_0_0; wire [161:0] tb_0_1; wire [161:0] tb_0_2; wire [161:0] tb_0_3; wire [161:0] tb_0_4; wire [161:0] tb_0_5; wire [161:0] tb_0_6; wire [161:0] tb_0_7; wire [161:0] tb_0_8; wire [161:0] tb_0_9; wire [161:0] tb_0_10; wire [161:0] tb_0_11; wire [161:0] tb_0_12; wire [161:0] tb_0_13; wire [161:0] tb_0_14; wire [161:0] tb_0_15; wire [161:0] tb_0_16; wire [161:0] tb_0_17; wire [161:0] tb_0_18; wire [161:0] tb_0_19; wire [161:0] tb_0_20; wire [161:0] tb_0_21; wire [161:0] tb_0_22;
wire [255:0] ta_0_0; wire [255:0] ta_0_1; wire [255:0] ta_0_2; wire [255:0] ta_0_3; wire [255:0] ta_0_4; wire [255:0] ta_0_5; wire [255:0] ta_0_6; wire [255:0] ta_0_7; wire [255:0] ta_0_8; wire [255:0] ta_0_9; wire [255:0] ta_0_10; wire [255:0] ta_0_11; wire [255:0] ta_0_12; wire [255:0] ta_0_13; wire [255:0] ta_0_14; wire [255:0] ta_0_15; wire [255:0] ta_0_16; wire [255:0] ta_0_17; wire [255:0] ta_0_18; wire [255:0] ta_0_19; wire [255:0] ta_0_20; wire [255:0] ta_0_21; wire [255:0] ta_0_22;
    assign ta_0_22 = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
wire [161:0] tb_1_0; wire [161:0] tb_1_1; wire [161:0] tb_1_2; wire [161:0] tb_1_3; wire [161:0] tb_1_4; wire [161:0] tb_1_5; wire [161:0] tb_1_6; wire [161:0] tb_1_7; wire [161:0] tb_1_8; wire [161:0] tb_1_9; wire [161:0] tb_1_10; wire [161:0] tb_1_11; wire [161:0] tb_1_12; wire [161:0] tb_1_13; wire [161:0] tb_1_14; wire [161:0] tb_1_15; wire [161:0] tb_1_16; wire [161:0] tb_1_17; wire [161:0] tb_1_18; wire [161:0] tb_1_19; wire [161:0] tb_1_20; wire [161:0] tb_1_21; wire [161:0] tb_1_22;
wire [255:0] ta_1_0; wire [255:0] ta_1_1; wire [255:0] ta_1_2; wire [255:0] ta_1_3; wire [255:0] ta_1_4; wire [255:0] ta_1_5; wire [255:0] ta_1_6; wire [255:0] ta_1_7; wire [255:0] ta_1_8; wire [255:0] ta_1_9; wire [255:0] ta_1_10; wire [255:0] ta_1_11; wire [255:0] ta_1_12; wire [255:0] ta_1_13; wire [255:0] ta_1_14; wire [255:0] ta_1_15; wire [255:0] ta_1_16; wire [255:0] ta_1_17; wire [255:0] ta_1_18; wire [255:0] ta_1_19; wire [255:0] ta_1_20; wire [255:0] ta_1_21; wire [255:0] ta_1_22;
    assign ta_1_22 = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
wire [161:0] tb_2_0; wire [161:0] tb_2_1; wire [161:0] tb_2_2; wire [161:0] tb_2_3; wire [161:0] tb_2_4; wire [161:0] tb_2_5; wire [161:0] tb_2_6; wire [161:0] tb_2_7; wire [161:0] tb_2_8; wire [161:0] tb_2_9; wire [161:0] tb_2_10; wire [161:0] tb_2_11; wire [161:0] tb_2_12; wire [161:0] tb_2_13; wire [161:0] tb_2_14; wire [161:0] tb_2_15; wire [161:0] tb_2_16; wire [161:0] tb_2_17; wire [161:0] tb_2_18; wire [161:0] tb_2_19; wire [161:0] tb_2_20; wire [161:0] tb_2_21; wire [161:0] tb_2_22;
wire [255:0] ta_2_0; wire [255:0] ta_2_1; wire [255:0] ta_2_2; wire [255:0] ta_2_3; wire [255:0] ta_2_4; wire [255:0] ta_2_5; wire [255:0] ta_2_6; wire [255:0] ta_2_7; wire [255:0] ta_2_8; wire [255:0] ta_2_9; wire [255:0] ta_2_10; wire [255:0] ta_2_11; wire [255:0] ta_2_12; wire [255:0] ta_2_13; wire [255:0] ta_2_14; wire [255:0] ta_2_15; wire [255:0] ta_2_16; wire [255:0] ta_2_17; wire [255:0] ta_2_18; wire [255:0] ta_2_19; wire [255:0] ta_2_20; wire [255:0] ta_2_21; wire [255:0] ta_2_22;
    assign ta_2_22 = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
wire [161:0] tb_3_0; wire [161:0] tb_3_1; wire [161:0] tb_3_2; wire [161:0] tb_3_3; wire [161:0] tb_3_4; wire [161:0] tb_3_5; wire [161:0] tb_3_6; wire [161:0] tb_3_7; wire [161:0] tb_3_8; wire [161:0] tb_3_9; wire [161:0] tb_3_10; wire [161:0] tb_3_11; wire [161:0] tb_3_12; wire [161:0] tb_3_13; wire [161:0] tb_3_14; wire [161:0] tb_3_15; wire [161:0] tb_3_16; wire [161:0] tb_3_17; wire [161:0] tb_3_18; wire [161:0] tb_3_19; wire [161:0] tb_3_20; wire [161:0] tb_3_21; wire [161:0] tb_3_22;
wire [255:0] ta_3_0; wire [255:0] ta_3_1; wire [255:0] ta_3_2; wire [255:0] ta_3_3; wire [255:0] ta_3_4; wire [255:0] ta_3_5; wire [255:0] ta_3_6; wire [255:0] ta_3_7; wire [255:0] ta_3_8; wire [255:0] ta_3_9; wire [255:0] ta_3_10; wire [255:0] ta_3_11; wire [255:0] ta_3_12; wire [255:0] ta_3_13; wire [255:0] ta_3_14; wire [255:0] ta_3_15; wire [255:0] ta_3_16; wire [255:0] ta_3_17; wire [255:0] ta_3_18; wire [255:0] ta_3_19; wire [255:0] ta_3_20; wire [255:0] ta_3_21; wire [255:0] ta_3_22;
    assign ta_3_22 = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
    (* keep *) reg [161:0] hb_0_0;  always @(posedge clk0e) hb_0_0 <= hbo_0;   // die seam relay
    (* keep *) reg [161:0] hb_0_1;  always @(posedge clk0e) hb_0_1 <= hb_0_0;   // die seam relay
    (* keep *) reg [161:0] hb_0_2;  always @(posedge clk0e) hb_0_2 <= hb_0_1;   // die seam relay
    assign tb_0_0 = hb_0_2;
    (* keep *) reg [255:0] hq_0_0;  always @(posedge clk0e) hq_0_0 <= ta_0_0;   // die seam relay
    (* keep *) reg [255:0] hq_0_1;  always @(posedge clk0e) hq_0_1 <= hq_0_0;   // die seam relay
    (* keep *) reg [255:0] hq_0_2;  always @(posedge clk0e) hq_0_2 <= hq_0_1;   // die seam relay
    assign hqo_0 = hq_0_2;
    (* keep *) reg [161:0] hb_1_0;  always @(posedge clk2e) hb_1_0 <= hbo_1;   // die seam relay
    (* keep *) reg [161:0] hb_1_1;  always @(posedge clk2e) hb_1_1 <= hb_1_0;   // die seam relay
    (* keep *) reg [161:0] hb_1_2;  always @(posedge clk2e) hb_1_2 <= hb_1_1;   // die seam relay
    assign tb_1_0 = hb_1_2;
    (* keep *) reg [255:0] hq_1_0;  always @(posedge clk2e) hq_1_0 <= ta_1_0;   // die seam relay
    (* keep *) reg [255:0] hq_1_1;  always @(posedge clk2e) hq_1_1 <= hq_1_0;   // die seam relay
    (* keep *) reg [255:0] hq_1_2;  always @(posedge clk2e) hq_1_2 <= hq_1_1;   // die seam relay
    assign hqo_1 = hq_1_2;
    (* keep *) reg [161:0] hb_2_0;  always @(posedge clk4e) hb_2_0 <= hbo_2;   // die seam relay
    (* keep *) reg [161:0] hb_2_1;  always @(posedge clk4e) hb_2_1 <= hb_2_0;   // die seam relay
    (* keep *) reg [161:0] hb_2_2;  always @(posedge clk4e) hb_2_2 <= hb_2_1;   // die seam relay
    assign tb_2_0 = hb_2_2;
    (* keep *) reg [255:0] hq_2_0;  always @(posedge clk4e) hq_2_0 <= ta_2_0;   // die seam relay
    (* keep *) reg [255:0] hq_2_1;  always @(posedge clk4e) hq_2_1 <= hq_2_0;   // die seam relay
    (* keep *) reg [255:0] hq_2_2;  always @(posedge clk4e) hq_2_2 <= hq_2_1;   // die seam relay
    assign hqo_2 = hq_2_2;
    (* keep *) reg [161:0] hb_3_0;  always @(posedge clk6e) hb_3_0 <= hbo_3;   // die seam relay
    (* keep *) reg [161:0] hb_3_1;  always @(posedge clk6e) hb_3_1 <= hb_3_0;   // die seam relay
    (* keep *) reg [161:0] hb_3_2;  always @(posedge clk6e) hb_3_2 <= hb_3_1;   // die seam relay
    assign tb_3_0 = hb_3_2;
    (* keep *) reg [255:0] hq_3_0;  always @(posedge clk6e) hq_3_0 <= ta_3_0;   // die seam relay
    (* keep *) reg [255:0] hq_3_1;  always @(posedge clk6e) hq_3_1 <= hq_3_0;   // die seam relay
    (* keep *) reg [255:0] hq_3_2;  always @(posedge clk6e) hq_3_2 <= hq_3_1;   // die seam relay
    assign hqo_3 = hq_3_2;
    hfd_hc_tile_xl u_tile_0 (.clk(clk0e), .bc_in(tb_0_0), .bc_out(tb_0_1), .acc_in(ta_0_1), .acc_out(ta_0_0));
    hfd_hc_tile_xl u_tile_1 (.clk(clk0e), .bc_in(tb_0_1), .bc_out(tb_0_2), .acc_in(ta_0_2), .acc_out(ta_0_1));
    hfd_hc_tile_xl u_tile_4 (.clk(clk0e), .bc_in(tb_0_2), .bc_out(tb_0_3), .acc_in(ta_0_3), .acc_out(ta_0_2));
    hfd_hc_tile_xl u_tile_5 (.clk(clk0e), .bc_in(tb_0_3), .bc_out(tb_0_4), .acc_in(ta_0_4), .acc_out(ta_0_3));
    hfd_hc_tile_xl u_tile_8 (.clk(clk0e), .bc_in(tb_0_4), .bc_out(tb_0_5), .acc_in(ta_0_5), .acc_out(ta_0_4));
    hfd_hc_tile_xl u_tile_9 (.clk(clk0w), .bc_in(tb_0_5), .bc_out(tb_0_6), .acc_in(ta_0_6), .acc_out(ta_0_5));
    hfd_hc_tile_xl u_tile_12 (.clk(clk0w), .bc_in(tb_0_6), .bc_out(tb_0_7), .acc_in(ta_0_7), .acc_out(ta_0_6));
    hfd_hc_tile_xl u_tile_13 (.clk(clk0w), .bc_in(tb_0_7), .bc_out(tb_0_8), .acc_in(ta_0_8), .acc_out(ta_0_7));
    hfd_hc_tile_xl u_tile_16 (.clk(clk0w), .bc_in(tb_0_8), .bc_out(tb_0_9), .acc_in(ta_0_9), .acc_out(ta_0_8));
    hfd_hc_tile_xl u_tile_17 (.clk(clk0w), .bc_in(tb_0_9), .bc_out(tb_0_10), .acc_in(ta_0_10), .acc_out(ta_0_9));
    hfd_hc_tile_xl u_tile_20 (.clk(clk0w), .bc_in(tb_0_10), .bc_out(tb_0_11), .acc_in(ta_0_11), .acc_out(ta_0_10));
    hfd_hc_tile_xl u_tile_21 (.clk(clk1w), .bc_in(tb_0_11), .bc_out(tb_0_12), .acc_in(ta_0_12), .acc_out(ta_0_11));
    hfd_hc_tile_xl u_tile_24 (.clk(clk1w), .bc_in(tb_0_12), .bc_out(tb_0_13), .acc_in(ta_0_13), .acc_out(ta_0_12));
    hfd_hc_tile_xl u_tile_25 (.clk(clk1w), .bc_in(tb_0_13), .bc_out(tb_0_14), .acc_in(ta_0_14), .acc_out(ta_0_13));
    hfd_hc_tile_xl u_tile_28 (.clk(clk1w), .bc_in(tb_0_14), .bc_out(tb_0_15), .acc_in(ta_0_15), .acc_out(ta_0_14));
    hfd_hc_tile_xl u_tile_29 (.clk(clk1w), .bc_in(tb_0_15), .bc_out(tb_0_16), .acc_in(ta_0_16), .acc_out(ta_0_15));
    hfd_hc_tile_xl u_tile_32 (.clk(clk1w), .bc_in(tb_0_16), .bc_out(tb_0_17), .acc_in(ta_0_17), .acc_out(ta_0_16));
    hfd_hc_tile_xl u_tile_33 (.clk(clk1e), .bc_in(tb_0_17), .bc_out(tb_0_18), .acc_in(ta_0_18), .acc_out(ta_0_17));
    hfd_hc_tile_xl u_tile_36 (.clk(clk1e), .bc_in(tb_0_18), .bc_out(tb_0_19), .acc_in(ta_0_19), .acc_out(ta_0_18));
    hfd_hc_tile_xl u_tile_37 (.clk(clk1e), .bc_in(tb_0_19), .bc_out(tb_0_20), .acc_in(ta_0_20), .acc_out(ta_0_19));
    hfd_hc_tile_xl u_tile_40 (.clk(clk1e), .bc_in(tb_0_20), .bc_out(tb_0_21), .acc_in(ta_0_21), .acc_out(ta_0_20));
    hfd_hc_tile_xl u_tile_41 (.clk(clk1e), .bc_in(tb_0_21), .bc_out(tb_0_22), .acc_in(ta_0_22), .acc_out(ta_0_21));
    hfd_hc_tile_xl u_tile_2 (.clk(clk2e), .bc_in(tb_1_0), .bc_out(tb_1_1), .acc_in(ta_1_1), .acc_out(ta_1_0));
    hfd_hc_tile_xl u_tile_3 (.clk(clk2e), .bc_in(tb_1_1), .bc_out(tb_1_2), .acc_in(ta_1_2), .acc_out(ta_1_1));
    hfd_hc_tile_xl u_tile_6 (.clk(clk2e), .bc_in(tb_1_2), .bc_out(tb_1_3), .acc_in(ta_1_3), .acc_out(ta_1_2));
    hfd_hc_tile_xl u_tile_7 (.clk(clk2e), .bc_in(tb_1_3), .bc_out(tb_1_4), .acc_in(ta_1_4), .acc_out(ta_1_3));
    hfd_hc_tile_xl u_tile_10 (.clk(clk2e), .bc_in(tb_1_4), .bc_out(tb_1_5), .acc_in(ta_1_5), .acc_out(ta_1_4));
    hfd_hc_tile_xl u_tile_11 (.clk(clk2w), .bc_in(tb_1_5), .bc_out(tb_1_6), .acc_in(ta_1_6), .acc_out(ta_1_5));
    hfd_hc_tile_xl u_tile_14 (.clk(clk2w), .bc_in(tb_1_6), .bc_out(tb_1_7), .acc_in(ta_1_7), .acc_out(ta_1_6));
    hfd_hc_tile_xl u_tile_15 (.clk(clk2w), .bc_in(tb_1_7), .bc_out(tb_1_8), .acc_in(ta_1_8), .acc_out(ta_1_7));
    hfd_hc_tile_xl u_tile_18 (.clk(clk2w), .bc_in(tb_1_8), .bc_out(tb_1_9), .acc_in(ta_1_9), .acc_out(ta_1_8));
    hfd_hc_tile_xl u_tile_19 (.clk(clk2w), .bc_in(tb_1_9), .bc_out(tb_1_10), .acc_in(ta_1_10), .acc_out(ta_1_9));
    hfd_hc_tile_xl u_tile_22 (.clk(clk2w), .bc_in(tb_1_10), .bc_out(tb_1_11), .acc_in(ta_1_11), .acc_out(ta_1_10));
    hfd_hc_tile_xl u_tile_23 (.clk(clk3w), .bc_in(tb_1_11), .bc_out(tb_1_12), .acc_in(ta_1_12), .acc_out(ta_1_11));
    hfd_hc_tile_xl u_tile_26 (.clk(clk3w), .bc_in(tb_1_12), .bc_out(tb_1_13), .acc_in(ta_1_13), .acc_out(ta_1_12));
    hfd_hc_tile_xl u_tile_27 (.clk(clk3w), .bc_in(tb_1_13), .bc_out(tb_1_14), .acc_in(ta_1_14), .acc_out(ta_1_13));
    hfd_hc_tile_xl u_tile_30 (.clk(clk3w), .bc_in(tb_1_14), .bc_out(tb_1_15), .acc_in(ta_1_15), .acc_out(ta_1_14));
    hfd_hc_tile_xl u_tile_31 (.clk(clk3w), .bc_in(tb_1_15), .bc_out(tb_1_16), .acc_in(ta_1_16), .acc_out(ta_1_15));
    hfd_hc_tile_xl u_tile_34 (.clk(clk3w), .bc_in(tb_1_16), .bc_out(tb_1_17), .acc_in(ta_1_17), .acc_out(ta_1_16));
    hfd_hc_tile_xl u_tile_35 (.clk(clk3e), .bc_in(tb_1_17), .bc_out(tb_1_18), .acc_in(ta_1_18), .acc_out(ta_1_17));
    hfd_hc_tile_xl u_tile_38 (.clk(clk3e), .bc_in(tb_1_18), .bc_out(tb_1_19), .acc_in(ta_1_19), .acc_out(ta_1_18));
    hfd_hc_tile_xl u_tile_39 (.clk(clk3e), .bc_in(tb_1_19), .bc_out(tb_1_20), .acc_in(ta_1_20), .acc_out(ta_1_19));
    hfd_hc_tile_xl u_tile_42 (.clk(clk3e), .bc_in(tb_1_20), .bc_out(tb_1_21), .acc_in(ta_1_21), .acc_out(ta_1_20));
    hfd_hc_tile_xl u_tile_43 (.clk(clk3e), .bc_in(tb_1_21), .bc_out(tb_1_22), .acc_in(ta_1_22), .acc_out(ta_1_21));
    hfd_hc_tile_xl u_tile_44 (.clk(clk4e), .bc_in(tb_2_0), .bc_out(tb_2_1), .acc_in(ta_2_1), .acc_out(ta_2_0));
    hfd_hc_tile_xl u_tile_45 (.clk(clk4e), .bc_in(tb_2_1), .bc_out(tb_2_2), .acc_in(ta_2_2), .acc_out(ta_2_1));
    hfd_hc_tile_xl u_tile_48 (.clk(clk4e), .bc_in(tb_2_2), .bc_out(tb_2_3), .acc_in(ta_2_3), .acc_out(ta_2_2));
    hfd_hc_tile_xl u_tile_49 (.clk(clk4e), .bc_in(tb_2_3), .bc_out(tb_2_4), .acc_in(ta_2_4), .acc_out(ta_2_3));
    hfd_hc_tile_xl u_tile_52 (.clk(clk4e), .bc_in(tb_2_4), .bc_out(tb_2_5), .acc_in(ta_2_5), .acc_out(ta_2_4));
    hfd_hc_tile_xl u_tile_53 (.clk(clk4w), .bc_in(tb_2_5), .bc_out(tb_2_6), .acc_in(ta_2_6), .acc_out(ta_2_5));
    hfd_hc_tile_xl u_tile_56 (.clk(clk4w), .bc_in(tb_2_6), .bc_out(tb_2_7), .acc_in(ta_2_7), .acc_out(ta_2_6));
    hfd_hc_tile_xl u_tile_57 (.clk(clk4w), .bc_in(tb_2_7), .bc_out(tb_2_8), .acc_in(ta_2_8), .acc_out(ta_2_7));
    hfd_hc_tile_xl u_tile_60 (.clk(clk4w), .bc_in(tb_2_8), .bc_out(tb_2_9), .acc_in(ta_2_9), .acc_out(ta_2_8));
    hfd_hc_tile_xl u_tile_61 (.clk(clk4w), .bc_in(tb_2_9), .bc_out(tb_2_10), .acc_in(ta_2_10), .acc_out(ta_2_9));
    hfd_hc_tile_xl u_tile_64 (.clk(clk4w), .bc_in(tb_2_10), .bc_out(tb_2_11), .acc_in(ta_2_11), .acc_out(ta_2_10));
    hfd_hc_tile_xl u_tile_65 (.clk(clk5w), .bc_in(tb_2_11), .bc_out(tb_2_12), .acc_in(ta_2_12), .acc_out(ta_2_11));
    hfd_hc_tile_xl u_tile_68 (.clk(clk5w), .bc_in(tb_2_12), .bc_out(tb_2_13), .acc_in(ta_2_13), .acc_out(ta_2_12));
    hfd_hc_tile_xl u_tile_69 (.clk(clk5w), .bc_in(tb_2_13), .bc_out(tb_2_14), .acc_in(ta_2_14), .acc_out(ta_2_13));
    hfd_hc_tile_xl u_tile_72 (.clk(clk5w), .bc_in(tb_2_14), .bc_out(tb_2_15), .acc_in(ta_2_15), .acc_out(ta_2_14));
    hfd_hc_tile_xl u_tile_73 (.clk(clk5w), .bc_in(tb_2_15), .bc_out(tb_2_16), .acc_in(ta_2_16), .acc_out(ta_2_15));
    hfd_hc_tile_xl u_tile_76 (.clk(clk5w), .bc_in(tb_2_16), .bc_out(tb_2_17), .acc_in(ta_2_17), .acc_out(ta_2_16));
    hfd_hc_tile_xl u_tile_77 (.clk(clk5e), .bc_in(tb_2_17), .bc_out(tb_2_18), .acc_in(ta_2_18), .acc_out(ta_2_17));
    hfd_hc_tile_xl u_tile_80 (.clk(clk5e), .bc_in(tb_2_18), .bc_out(tb_2_19), .acc_in(ta_2_19), .acc_out(ta_2_18));
    hfd_hc_tile_xl u_tile_81 (.clk(clk5e), .bc_in(tb_2_19), .bc_out(tb_2_20), .acc_in(ta_2_20), .acc_out(ta_2_19));
    hfd_hc_tile_xl u_tile_84 (.clk(clk5e), .bc_in(tb_2_20), .bc_out(tb_2_21), .acc_in(ta_2_21), .acc_out(ta_2_20));
    hfd_hc_tile_xl u_tile_85 (.clk(clk5e), .bc_in(tb_2_21), .bc_out(tb_2_22), .acc_in(ta_2_22), .acc_out(ta_2_21));
    hfd_hc_tile_xl u_tile_46 (.clk(clk6e), .bc_in(tb_3_0), .bc_out(tb_3_1), .acc_in(ta_3_1), .acc_out(ta_3_0));
    hfd_hc_tile_xl u_tile_47 (.clk(clk6e), .bc_in(tb_3_1), .bc_out(tb_3_2), .acc_in(ta_3_2), .acc_out(ta_3_1));
    hfd_hc_tile_xl u_tile_50 (.clk(clk6e), .bc_in(tb_3_2), .bc_out(tb_3_3), .acc_in(ta_3_3), .acc_out(ta_3_2));
    hfd_hc_tile_xl u_tile_51 (.clk(clk6e), .bc_in(tb_3_3), .bc_out(tb_3_4), .acc_in(ta_3_4), .acc_out(ta_3_3));
    hfd_hc_tile_xl u_tile_54 (.clk(clk6e), .bc_in(tb_3_4), .bc_out(tb_3_5), .acc_in(ta_3_5), .acc_out(ta_3_4));
    hfd_hc_tile_xl u_tile_55 (.clk(clk6w), .bc_in(tb_3_5), .bc_out(tb_3_6), .acc_in(ta_3_6), .acc_out(ta_3_5));
    hfd_hc_tile_xl u_tile_58 (.clk(clk6w), .bc_in(tb_3_6), .bc_out(tb_3_7), .acc_in(ta_3_7), .acc_out(ta_3_6));
    hfd_hc_tile_xl u_tile_59 (.clk(clk6w), .bc_in(tb_3_7), .bc_out(tb_3_8), .acc_in(ta_3_8), .acc_out(ta_3_7));
    hfd_hc_tile_xl u_tile_62 (.clk(clk6w), .bc_in(tb_3_8), .bc_out(tb_3_9), .acc_in(ta_3_9), .acc_out(ta_3_8));
    hfd_hc_tile_xl u_tile_63 (.clk(clk6w), .bc_in(tb_3_9), .bc_out(tb_3_10), .acc_in(ta_3_10), .acc_out(ta_3_9));
    hfd_hc_tile_xl u_tile_66 (.clk(clk6w), .bc_in(tb_3_10), .bc_out(tb_3_11), .acc_in(ta_3_11), .acc_out(ta_3_10));
    hfd_hc_tile_xl u_tile_67 (.clk(clk7w), .bc_in(tb_3_11), .bc_out(tb_3_12), .acc_in(ta_3_12), .acc_out(ta_3_11));
    hfd_hc_tile_xl u_tile_70 (.clk(clk7w), .bc_in(tb_3_12), .bc_out(tb_3_13), .acc_in(ta_3_13), .acc_out(ta_3_12));
    hfd_hc_tile_xl u_tile_71 (.clk(clk7w), .bc_in(tb_3_13), .bc_out(tb_3_14), .acc_in(ta_3_14), .acc_out(ta_3_13));
    hfd_hc_tile_xl u_tile_74 (.clk(clk7w), .bc_in(tb_3_14), .bc_out(tb_3_15), .acc_in(ta_3_15), .acc_out(ta_3_14));
    hfd_hc_tile_xl u_tile_75 (.clk(clk7w), .bc_in(tb_3_15), .bc_out(tb_3_16), .acc_in(ta_3_16), .acc_out(ta_3_15));
    hfd_hc_tile_xl u_tile_78 (.clk(clk7w), .bc_in(tb_3_16), .bc_out(tb_3_17), .acc_in(ta_3_17), .acc_out(ta_3_16));
    hfd_hc_tile_xl u_tile_79 (.clk(clk7e), .bc_in(tb_3_17), .bc_out(tb_3_18), .acc_in(ta_3_18), .acc_out(ta_3_17));
    hfd_hc_tile_xl u_tile_82 (.clk(clk7e), .bc_in(tb_3_18), .bc_out(tb_3_19), .acc_in(ta_3_19), .acc_out(ta_3_18));
    hfd_hc_tile_xl u_tile_83 (.clk(clk7e), .bc_in(tb_3_19), .bc_out(tb_3_20), .acc_in(ta_3_20), .acc_out(ta_3_19));
    hfd_hc_tile_xl u_tile_86 (.clk(clk7e), .bc_in(tb_3_20), .bc_out(tb_3_21), .acc_in(ta_3_21), .acc_out(ta_3_20));
    hfd_hc_tile_xl u_tile_87 (.clk(clk7e), .bc_in(tb_3_21), .bc_out(tb_3_22), .acc_in(ta_3_22), .acc_out(ta_3_21));
endmodule
