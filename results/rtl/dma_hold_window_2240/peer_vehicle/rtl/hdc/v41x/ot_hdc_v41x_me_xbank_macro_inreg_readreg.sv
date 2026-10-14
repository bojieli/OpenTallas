`timescale 1ns/1ps
// Registered local cut for the 16-macro ME activation store.  The external
// producer's preload/write/read request is captured once before the SRAM
// ports; SRAM read and bank output are registered. Sustained service is one beat per
// cycle, with one additional request/write fill cycle versus the direct macro.
module ot_hdc_v41x_me_xbank_macro_inreg_readreg #(
    parameter integer MG=8,
    parameter integer MP=2,
    parameter integer G=4,
    parameter integer KMAX=5120,
    parameter integer NBW=14,
    parameter integer EW=13
) (
    input wire clk,
    input wire wr_v,
    input wire [$clog2(MP+1)-1:0] wr_p,
    input wire [EW-1:0] wr_e,
    input wire [G*16-1:0] wr_d,
    input wire pre_v,
    input wire [$clog2(MP+1)-1:0] pre_p,
    input wire [EW-1:0] pre_e,
    input wire [8*MG*16-1:0] pre_d,
    input wire [1:0] rd_rot,
    input wire [7:0] rq_v,
    input wire [8*NBW-1:0] rq_q,
    input wire [8*4-1:0] rq_plg,
    output wire [8*MG*MP*16-1:0] rd_x
);
    reg wr_v_r,pre_v_r;
    reg [$clog2(MP+1)-1:0] wr_p_r,pre_p_r;
    reg [EW-1:0] wr_e_r,pre_e_r;
    reg [G*16-1:0] wr_d_r;
    reg [8*MG*16-1:0] pre_d_r;
    reg [1:0] rd_rot_r;
    reg [7:0] rq_v_r;
    reg [8*NBW-1:0] rq_q_r;
    reg [8*4-1:0] rq_plg_r;
    always @(posedge clk) begin
        wr_v_r<=wr_v; wr_p_r<=wr_p; wr_e_r<=wr_e; wr_d_r<=wr_d;
        pre_v_r<=pre_v; pre_p_r<=pre_p; pre_e_r<=pre_e; pre_d_r<=pre_d;
        rd_rot_r<=rd_rot; rq_v_r<=rq_v; rq_q_r<=rq_q; rq_plg_r<=rq_plg;
    end
    ot_hdc_v41x_me_xbank_macro_readreg #(.MG(MG),.MP(MP),.G(G),.KMAX(KMAX),.NBW(NBW),.EW(EW)) u_store (
        .clk(clk),.wr_v(wr_v_r),.wr_p(wr_p_r),.wr_e(wr_e_r),.wr_d(wr_d_r),
        .pre_v(pre_v_r),.pre_p(pre_p_r),.pre_e(pre_e_r),.pre_d(pre_d_r),
        .rd_rot(rd_rot_r),.rq_v(rq_v_r),.rq_q(rq_q_r),.rq_plg(rq_plg_r),.rd_x(rd_x));
endmodule
