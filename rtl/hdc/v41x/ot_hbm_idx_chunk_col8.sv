`timescale 1ns/1ps
`default_nettype none
// Baseline integration, same clocks/active edges; mesochronous seams remain OPEN.
module ot_hbm_idx_chunk_col8 #(
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
 ot_hidx_chunk_glue #(.QLATE(QLATE)) u_glue (.clk(clk),.rst_n(rst_n),.hb(hb),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.k_v(k_v),.k_kv(k_kv),.k_key(k_key),.c_v(c_v),.c_kv(c_kv),.c_sum(c_sum),.c_fault(c_fault),.online(online),.n_v(n_v),.n_kv(n_kv),.n_sum(n_sum),.n_fault(n_fault),.col_rst_n(crst),.col_qv(cqv),.col_q(cq),.col_key(ckey),.col_hid(chid),.col_cs(ccs),.col_cf(ccf),.col_prdy(cprdy));
 genvar g;
 for(g=0;g<4;g=g+1) begin:g_col
  wire [31:0] cs[0:4]; wire cf[0:4];
  assign cs[0]=0;assign cf[0]=0;
  // Preserve COL8's two face reset stages independently at every column.
  (* async_reg="true",keep="true",dont_touch="true" *) reg[1:0] sync_q;
  always @(posedge clk or negedge crst[g]) if(!crst[g])sync_q<=0;else sync_q<={sync_q[0],1'b1};
  ot_hidx_score_pair8_r0 u_pair0(.clk(clk_pair[4*g+0]),.rst_n(sync_q[1]),.qv_b(cqv),.q_b(cq),.key(ckey[544*g+:544]),.hid(chid[0+:16]),.cs_out(cs[1]),.cf_out(cf[1]),.prdy(cprdy[4*g+0]));
  ot_hidx_score_pair8_r1 u_pair1(.clk(clk_pair[4*g+1]),.rst_n(sync_q[1]),.qv_b(cqv),.q_b(cq),.key(ckey[544*g+:544]),.hid(chid[16+:16]),.cs_in(cs[1]),.cf_in(cf[1]),.cs_out(cs[2]),.cf_out(cf[2]),.prdy(cprdy[4*g+1]));
  ot_hidx_score_pair8_r2 u_pair2(.clk(clk_pair[4*g+2]),.rst_n(sync_q[1]),.qv_b(cqv),.q_b(cq),.key(ckey[544*g+:544]),.hid(chid[32+:16]),.cs_in(cs[2]),.cf_in(cf[2]),.cs_out(cs[3]),.cf_out(cf[3]),.prdy(cprdy[4*g+2]));
  ot_hidx_score_pair8_r3 u_pair3(.clk(clk_pair[4*g+3]),.rst_n(sync_q[1]),.qv_b(cqv),.q_b(cq),.key(ckey[544*g+:544]),.hid(chid[48+:16]),.cs_in(cs[3]),.cf_in(cf[3]),.cs_out(cs[4]),.cf_out(cf[4]),.prdy(cprdy[4*g+3]));
  assign ccs[32*g+:32]=cs[4];assign ccf[g]=cf[4];
 end
endmodule
`default_nettype wire
