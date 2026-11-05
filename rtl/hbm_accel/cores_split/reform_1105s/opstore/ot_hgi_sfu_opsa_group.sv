// HBM-FORM-SPLIT d44v part 27: one operand group of ot_hgi_sfu_static_operand_store as a tile: g_operand[G] whole (request and stage decode,
// scalar read path, rd_q mux, lgroup2) plus scalar_data_q[G]. Every input is an uncut-core pin, so the shell's +1/+1 keeps every read and stage date.
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_sfu_opsa_gblock #(parameter [1:0] G = 2'd0) (
    input  wire          clk, rst_n,
    input  wire          scalar_load, scalar_enable,
    input  wire [31:0]   scalar_data,
    input  wire [15:0]   rd_re,
    input  wire [383:0]  rd_addr,
    input  wire [31:0]   rd_src,
    output wire [511:0]  rd_q,
    input  wire [7:0]    stage_v,
    input  wire [15:0]   stage_group,
    input  wire [119:0]  stage_addr,
    input  wire [2047:0] stage_data,
    output wire          flt
);
    reg  [31:0]  scalar_data_q;
    reg  [511:0] scalar_read;
    reg          scalar_selected;
    wire [15:0]  req;
    wire [511:0] data;
    wire [7:0]   sw;
    always @(posedge clk) begin
        if (scalar_load) scalar_data_q <= scalar_data;
        scalar_selected <= scalar_enable;
        for (integer l = 0; l < 16; l = l + 1)
            if (rd_re[l] && scalar_enable) scalar_read[32*l +: 32] <= scalar_data_q;
    end
    for (genvar l = 0; l < 16; l = l + 1) begin : g_lane
        assign req[l] = rd_re[l] && rd_src[2*l +: 2] == 2'd0 && !scalar_enable;
        assign rd_q[32*l +: 32] = scalar_selected ? scalar_read[32*l +: 32] : data[32*l +: 32];
    end
    for (genvar b = 0; b < 8; b = b + 1) begin : g_stage
        assign sw[b] = stage_v[b] && stage_group[2*b +: 2] == G;
    end
    ot_hgi_su_lgroup2_lf #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(0),.MACRO(1),.MUT_XBAR(0),.NS(8)) u_g (
        .clk(clk), .rst_n(rst_n), .rq(req), .rr(req), .ra(rd_addr), .rd(data),
        .sr_v(8'd0), .sr_addr(120'd0), .sr_d(), .sr_rv(),
        .sw_v(sw), .sw_addr(stage_addr), .sw_mask(64'hffffffffffffffff), .sw_d(stage_data),
        .lw(1'b0), .lwa(24'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
endmodule
module ot_hgi_sfu_opsa_group0 (
    input  wire clk, rst_n, scalar_load, scalar_enable, input wire [31:0] scalar_data, input wire [15:0] rd_re, input wire [383:0] rd_addr, input wire [31:0] rd_src,
    output wire [511:0] rd_q, input wire [7:0] stage_v, input wire [15:0] stage_group, input wire [119:0] stage_addr, input wire [2047:0] stage_data, output wire flt);
    ot_hgi_sfu_opsa_gblock #(.G(2'd0)) u_t (.*);
endmodule
module ot_hgi_sfu_opsa_group1 (
    input  wire clk, rst_n, scalar_load, scalar_enable, input wire [31:0] scalar_data, input wire [15:0] rd_re, input wire [383:0] rd_addr, input wire [31:0] rd_src,
    output wire [511:0] rd_q, input wire [7:0] stage_v, input wire [15:0] stage_group, input wire [119:0] stage_addr, input wire [2047:0] stage_data, output wire flt);
    ot_hgi_sfu_opsa_gblock #(.G(2'd1)) u_t (.*);
endmodule
`default_nettype wire
