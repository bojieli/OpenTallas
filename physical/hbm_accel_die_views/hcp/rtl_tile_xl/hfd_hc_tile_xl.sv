`timescale 1ns/1ps
// tools/hbm_hub_quarter_gen.py --tiled: hfd_hc_tile = one ot_dsrom_su_hcpost_lane_pr + its broadcast / capture / accumulate registers
module hfd_hc_tile_xl (
    input  wire clk,
    input  wire [161:0] bc_in,
    output reg  [161:0] bc_out,
    input  wire [255:0] acc_in,
    output reg  [255:0] acc_out
);
    (* keep *) reg [161:0] bcq;
    always @(posedge clk) bcq <= bc_in;
    wire [161:0] bc_pos;
    assign bc_pos = {bcq[161], bcq[123:0], bcq[160:124]};
    wire [33:0] lo;
    ot_dsrom_su_hcpost_lane_pr `ifndef SYNTHESIS #(.ML(7), .AL(6)) `endif u_lane (.clk(clk), .rst_n(~bcq[161]), .v(bcq[0:0]), .r0({bcq[59], bcq[52], bcq[45], bcq[38], bcq[31], bcq[24], bcq[17], bcq[10], bcq[3], bcq[157], bcq[150], bcq[143], bcq[136], bcq[129], bcq[122], bcq[115], bcq[108], bcq[101], bcq[94], bcq[87], bcq[80], bcq[73], bcq[66], bcq[59], bcq[52], bcq[45], bcq[38], bcq[31], bcq[24], bcq[17], bcq[10], bcq[3]}), .r1({bcq[122], bcq[115], bcq[108], bcq[101], bcq[94], bcq[87], bcq[80], bcq[73], bcq[66], bcq[59], bcq[52], bcq[45], bcq[38], bcq[31], bcq[24], bcq[17], bcq[10], bcq[3], bcq[157], bcq[150], bcq[143], bcq[136], bcq[129], bcq[122], bcq[115], bcq[108], bcq[101], bcq[94], bcq[87], bcq[80], bcq[73], bcq[66]}), .r2({bcq[24], bcq[17], bcq[10], bcq[3], bcq[157], bcq[150], bcq[143], bcq[136], bcq[129], bcq[122], bcq[115], bcq[108], bcq[101], bcq[94], bcq[87], bcq[80], bcq[73], bcq[66], bcq[59], bcq[52], bcq[45], bcq[38], bcq[31], bcq[24], bcq[17], bcq[10], bcq[3], bcq[157], bcq[150], bcq[143], bcq[136], bcq[129]}), .r3({bcq[87], bcq[80], bcq[73], bcq[66], bcq[59], bcq[52], bcq[45], bcq[38], bcq[31], bcq[24], bcq[17], bcq[10], bcq[3], bcq[157], bcq[150], bcq[143], bcq[136], bcq[129], bcq[122], bcq[115], bcq[108], bcq[101], bcq[94], bcq[87], bcq[80], bcq[73], bcq[66], bcq[59], bcq[52], bcq[45], bcq[38], bcq[31]}), .y({bcq[150], bcq[143], bcq[136], bcq[129], bcq[122], bcq[115], bcq[108], bcq[101], bcq[94], bcq[87], bcq[80], bcq[73], bcq[66], bcq[59], bcq[52], bcq[45], bcq[38], bcq[31], bcq[24], bcq[17], bcq[10], bcq[3], bcq[157], bcq[150], bcq[143], bcq[136], bcq[129], bcq[122], bcq[115], bcq[108], bcq[101], bcq[94]}), .c0(bcq[32:1]), .c1(bcq[64:33]), .c2(bcq[96:65]), .c3(bcq[128:97]), .p(bcq[160:129]), .vo(lo[0:0]), .o(lo[32:1]), .fault(lo[33:33]));
    (* keep *) reg [33:0] lq;
    always @(posedge clk) lq <= lo;
    wire [255:0] acc_r = {acc_in[221:0], acc_in[255:222]};
    reg [255:0] acc_pos;
    always @(posedge clk) acc_pos <= acc_r ^ {222'd0, lq};
`ifdef OT_HC_TILE_MUT_NOLOCKUP
    always @(*) begin bc_out = bc_pos; acc_out = acc_pos; end
`else
    always @(negedge clk) begin bc_out <= bc_pos; acc_out <= acc_pos; end
`endif
endmodule
