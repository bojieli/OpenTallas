`timescale 1ns/1ps
`default_nettype none
// Baseline integration, same clocks/active edges; mesochronous seams remain OPEN.
module ot_hbm_idx_chunk_col8_face #(
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
 wire [3:0] crst; wire cqv; wire [567:0] cq; wire [2175:0] ckey; wire [63:0] chid;
 wire [127:0] ccs; wire [3:0] ccf; wire [15:0] cprdy;
 ot_hidx_chunk_glue #(.QLATE(QLATE),.VL_EXTRA(23)) u_glue (.clk(clk),.rst_n(rst_n),.hb(hb),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.k_v(k_v),.k_kv(k_kv),.k_key(k_key),.c_v(c_v),.c_kv(c_kv),.c_sum(c_sum),.c_fault(c_fault),.online(online),.n_v(n_v),.n_kv(n_kv),.n_sum(n_sum),.n_fault(n_fault),.col_rst_n(crst),.col_qv(cqv),.col_q(cq),.col_key(ckey),.col_hid(chid),.col_cs(ccs),.col_cf(ccf),.col_prdy(cprdy));
 genvar g;
 for(g=0;g<4;g=g+1) begin:g_col
  ot_hidx_col8_sram_face_col u_col(.ctl(clk),.cp(clk_pair[4*g+:4]),.rst_n(crst[g]),.qv_b(cqv),.q_b(cq),.key(ckey[544*g+:544]),.hid(chid),.cs_out(ccs[32*g+:32]),.cf_out(ccf[g]),.prdy(cprdy[4*g+:4]));
 end
endmodule
`default_nettype wire
