`timescale 1ns/1ps
`default_nettype none
// Baseline integration, same clocks/active edges; mesochronous seams remain OPEN.
module ot_hbm_idx_chunk_col8_rejoined #(
    parameter integer QLATE = 0          // bench mutant: the query broadcast reaches the heads QLATE edges late
) (
    input  wire                  clk, input wire [15:0] clk_pair,
    input  wire                  rst_n,
    input  wire [7:0]            hb,
    input  wire                  ql_v,
    input  wire [7:0]            ql_head,
    input  wire [NB*128-1:0]     ql_codes,
    input  wire [NB*8-1:0]       ql_sc,
    input  wire [15:0]           ql_w,
    input  wire                  k_v,
    input  wire [NKT-1:0]        k_kv,
    input  wire [NKT*NB*136-1:0] k_key,
    output wire                   c_v,
    output wire  [NKT-1:0]        c_kv,
    output wire  [NKT*32-1:0]     c_sum,
    output wire  [NKT-1:0]        c_fault,
    output wire                   online,
    // the D inputs of c_* (for the chained leaf: its sum-bus register replaces the c_* register, reg -> reg)
    output wire                  n_v,
    output wire [NKT-1:0]        n_kv,
    output wire [NKT*32-1:0]     n_sum,
    output wire [NKT-1:0]        n_fault
);

 localparam integer NB=4,NKT=4;
 wire [3:0] cut_rst_n;
 wire [3:0] cut_qv;
 wire [2271:0] cut_q;
 wire [2175:0] cut_key;
 wire [255:0] cut_hid;
 wire [127:0] cut_cs;
 wire [3:0] cut_cf;
 wire [15:0] cut_prdy;
 ot_hbm_idx_chunk_col8_control #(.QLATE(QLATE)) u_control(.clk(clk),.clk_pair(clk_pair),.rst_n(rst_n),.hb(hb),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.k_v(k_v),.k_kv(k_kv),.k_key(k_key),.c_v(c_v),.c_kv(c_kv),.c_sum(c_sum),.c_fault(c_fault),.online(online),.n_v(n_v),.n_kv(n_kv),.n_sum(n_sum),.n_fault(n_fault),.cut_rst_n(cut_rst_n),.cut_qv(cut_qv),.cut_q(cut_q),.cut_key(cut_key),.cut_hid(cut_hid),.cut_cs(cut_cs),.cut_cf(cut_cf),.cut_prdy(cut_prdy));
 for(genvar g=0;g<4;g=g+1)begin:g_col
  ot_hidx_col8_sram_face_col u_col(.ctl(clk),.cp(clk_pair[g*4+:4]),.rst_n(cut_rst_n[g]),.qv_b(cut_qv[g]),.q_b(cut_q[g*568+:568]),.key(cut_key[g*544+:544]),.hid(cut_hid[g*64+:64]),.cs_out(cut_cs[g*32+:32]),.cf_out(cut_cf[g]),.prdy(cut_prdy[g*4+:4]));
 end
endmodule
`default_nettype wire
