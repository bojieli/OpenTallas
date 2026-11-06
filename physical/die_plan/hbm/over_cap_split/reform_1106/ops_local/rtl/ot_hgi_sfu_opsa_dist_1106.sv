// Distinct source capability: column-local stage write cohort; stage-write visibility +1, all read/scalar response latency unchanged.
// HBM-REFORM-B10: IREG = 1 (registered tile inputs) + lgroup2_lf FREG = 1: rd_q +2 edges, flt +2 edges (COORD 15:16 pre-approved).
// HBM-REFORM-B9: lgroup2_lf BREG = 1 (registered bank inputs): data and the scalar read path both +1 edge, so rd_q is +1 edge.
// HBM-FORM-SPLIT d44v part 27: one operand group of ot_hgi_sfu_static_operand_store as a tile: g_operand[G] whole (request and stage decode,
// scalar read path, rd_q mux, lgroup2) plus scalar_data_q[G]. Every input is an uncut-core pin, so the shell's +1/+1 keeps every read and stage date.
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_sfu_opsa_gblock_dist_1106 #(parameter [1:0] G = 2'd0, parameter integer IREG = 1) (
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
    // HBM-REFORM-B10 IREG = 1: one more register stage on every input (no reset, so every op issued keeps its order and
    // lands), before the request / stage decode and the lgroup2 selects. All reads and writes move one edge together:
    // rd_q +2 edges and flt +2 edges in total with BREG / FREG.
    wire         scalar_load_i, scalar_enable_i; wire [31:0] scalar_data_i; wire [15:0] rd_re_i; wire [383:0] rd_addr_i;
    wire [31:0]  rd_src_i; wire [7:0] stage_v_i; wire [15:0] stage_group_i; wire [119:0] stage_addr_i; wire [2047:0] stage_data_i;
    if (IREG != 0) begin : g_ireg
        reg q_sl, q_se; reg [31:0] q_sd; reg [15:0] q_re; reg [383:0] q_ra; reg [31:0] q_rs; reg [7:0] q_sv; reg [15:0] q_sg;
        reg [119:0] q_sa; reg [2047:0] q_sdat;
        always @(posedge clk) begin
            q_sl <= scalar_load; q_se <= scalar_enable; q_sd <= scalar_data; q_re <= rd_re; q_ra <= rd_addr; q_rs <= rd_src;
            q_sv <= stage_v; q_sg <= stage_group; q_sa <= stage_addr; q_sdat <= stage_data;
        end
        assign scalar_load_i = q_sl; assign scalar_enable_i = q_se; assign scalar_data_i = q_sd; assign rd_re_i = q_re;
        assign rd_addr_i = q_ra; assign rd_src_i = q_rs; assign stage_v_i = q_sv; assign stage_group_i = q_sg;
        assign stage_addr_i = q_sa; assign stage_data_i = q_sdat;
    end else begin : g_noireg
        assign scalar_load_i = scalar_load; assign scalar_enable_i = scalar_enable; assign scalar_data_i = scalar_data;
        assign rd_re_i = rd_re; assign rd_addr_i = rd_addr; assign rd_src_i = rd_src; assign stage_v_i = stage_v;
        assign stage_group_i = stage_group; assign stage_addr_i = stage_addr; assign stage_data_i = stage_data;
    end
    reg  [31:0]  scalar_data_q;
    reg  [511:0] scalar_read;
    reg          scalar_selected, scalar_selected2;
    reg  [511:0] scalar_read2;
    wire [15:0]  req;
    wire [511:0] data;
    wire [7:0]   sw;
    always @(posedge clk) begin
        if (scalar_load_i) scalar_data_q <= scalar_data_i;
        scalar_selected <= scalar_enable_i; scalar_selected2 <= scalar_selected; scalar_read2 <= scalar_read;
        for (integer l = 0; l < 16; l = l + 1)
            if (rd_re_i[l] && scalar_enable_i) scalar_read[32*l +: 32] <= scalar_data_q;
    end
    for (genvar l = 0; l < 16; l = l + 1) begin : g_lane
        assign req[l] = rd_re_i[l] && rd_src_i[2*l +: 2] == 2'd0 && !scalar_enable_i;
        assign rd_q[32*l +: 32] = scalar_selected2 ? scalar_read2[32*l +: 32] : data[32*l +: 32];
    end
    for (genvar b = 0; b < 8; b = b + 1) begin : g_stage
        assign sw[b] = stage_v_i[b] && stage_group_i[2*b +: 2] == G;
    end
    ot_hgi_su_lgroup2_local_1106 #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(0),.MACRO(1),.MUT_XBAR(0),.NS(8),.BREG(1),.FREG(1),.DREG(1)) u_g (
        .clk(clk), .rst_n(rst_n), .rq(req), .rr(req), .ra(rd_addr_i), .rd(data),
        .sr_v(8'd0), .sr_addr(120'd0), .sr_d(), .sr_rv(),
        .sw_v(sw), .sw_addr(stage_addr_i), .sw_mask(64'hffffffffffffffff), .sw_d(stage_data_i),
        .lw(1'b0), .lwa(24'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
endmodule
module ot_hgi_sfu_opsa_group0_dist_1106__fcore (
    input  wire clk, rst_n, scalar_load, scalar_enable, input wire [31:0] scalar_data, input wire [15:0] rd_re, input wire [383:0] rd_addr, input wire [31:0] rd_src,
    output wire [511:0] rd_q, input wire [7:0] stage_v, input wire [15:0] stage_group, input wire [119:0] stage_addr, input wire [2047:0] stage_data, output wire flt);
    ot_hgi_sfu_opsa_gblock_dist_1106 #(.G(2'd0)) u_t (.*);
endmodule
module ot_hgi_sfu_opsa_group1_dist_1106__fcore (
    input  wire clk, rst_n, scalar_load, scalar_enable, input wire [31:0] scalar_data, input wire [15:0] rd_re, input wire [383:0] rd_addr, input wire [31:0] rd_src,
    output wire [511:0] rd_q, input wire [7:0] stage_v, input wire [15:0] stage_group, input wire [119:0] stage_addr, input wire [2047:0] stage_data, output wire flt);
    ot_hgi_sfu_opsa_gblock_dist_1106 #(.G(2'd1)) u_t (.*);
endmodule
`default_nettype wire
